import json
import os
import subprocess
from typing import Dict, List, Set, Tuple, TypeVar

import numpy as np
import pandas as pd
import requests
import tqdm
from configs import CLIP_EMBEDDINGS, DATA_DIRECTORY, DEFAULT_SIZE
from database.main import get_db, image_collection
from database.utils import segments_to_events
from query_parse.types.requests import Data
from results.models import Event, Image
from retrieval.async_utils import timer
from rich import print as rprint
from sklearn.cluster import KMeans

from visual.features import SIGLIP_FEATURES
from visual.low_visual import blurred_indices
from visual.main import get_model


def compare_images(data: Data, image1: dict, image2: dict):
    """
    For the LSC23 dataset, fixed boundaries are:
    - different locations
    - time gap where the camera is off
    For Deakin, fixed boundaries are:
    - different patientID
    - time gap where the camera is off
    """
    time_gap = 60 * 5  # 5 minutes
    if data == Data.LSC23:
        if image1["location"] != image2["location"]:
            return True
        if (image1["utc_time"] - image2["utc_time"]).total_seconds() > time_gap:
            return True
    elif data == Data.Deakin:
        if image1["patient"]["id"] != image2["patient"]["id"]:
            return True
        if (
            image1["snap"]["local_time"] - image2["snap"]["local_time"]
        ).total_seconds() > time_gap:
            return True
        if image1["date"] != image2["date"]:
            return True
    elif data == Data.CASTLE:
        time_gap = 5  # 5 seconds
        if image1["day"] != image2["day"]:
            return True
        if image1["person"] != image2["person"]:
            return True
        if (image1["utc_time"] - image2["utc_time"]).total_seconds() > time_gap:
            return True
    return False


def get_fixed_boundaries(data):
    print(f"Finding fixed boundaries for {data}...")
    sort_criteria = None
    if data == Data.LSC23:
        sort_criteria = [("utc_time", 1)]
    elif data == Data.Deakin:
        sort_criteria = [("patient.id", 1), ("snap.local_time", 1)]
    elif data == Data.CASTLE:
        sort_criteria = [("day", 1), ("person", 1), ("utc_time", 1)]

    boundaries: set[int] = set()
    prev_image = None
    pbar = tqdm.tqdm(
        desc=f"Finding fixed boundaries for {data}",
        total=image_collection(get_db(data)).count_documents({}),
    )
    if data == Data.CASTLE:
        # split into days and persons
        days = image_collection(get_db(data)).distinct("day")
        persons = image_collection(get_db(data)).distinct("person")
        for day in days:
            for person in persons:
                first_image = True
                images = (
                    image_collection(get_db(data))
                    .find({"day": day, "person": person})
                    .sort([("utc_time", 1)])
                )
                pbar.set_description(
                    f"Finding fixed boundaries for {data} - {day} - {person}"
                )
                for image_data in images:
                    pbar.update(1)
                    if first_image:
                        boundaries.add(
                            SIGLIP_FEATURES[data].ids.index(image_data["image"])
                        )
                        first_image = False
                    elif prev_image is not None:
                        if compare_images(data, prev_image, image_data):
                            try:
                                boundaries.add(
                                    SIGLIP_FEATURES[data].ids.index(prev_image["image"])
                                )
                            except ValueError:
                                pass
                    prev_image = image_data
        print(boundaries)
    else:
        for image_data in image_collection(get_db(data)).find().sort(sort_criteria):
            pbar.update(1)
            if prev_image is not None:
                if compare_images(data, prev_image, image_data):
                    try:
                        boundaries.add(
                            SIGLIP_FEATURES[data].ids.index(prev_image["image"])
                        )
                    except ValueError:
                        pass
            prev_image = image_data
    return boundaries


def create_new_segments(
    data: Data, photo_ids: List[str], features: np.ndarray, blurred: Set[int]
) -> List[Tuple[int, int]]:
    print(f"Creating new segments for {data}, with {len(photo_ids)} photos...")
    fixed_boundaries = get_fixed_boundaries(data)
    # Segment the data
    # sort features by the photo_ids
    print(f"Found {len(fixed_boundaries)} fixed boundaries for {data}.")
    all_sims = []

    for i in range(len(photo_ids) - 1):
        j = i + 1
        sim = features[i] @ features[j].T
        all_sims.append(sim)

    # Threshold for similarity
    threshold = 0.0403

    # Threshold for segment
    threshold = np.percentile(all_sims, 80)

    # Get segments from left to right
    segments: list[tuple[int, int]] = []
    start = 0
    end = 1

    while end < len(photo_ids) and start < len(photo_ids):
        is_boundary = False
        # check if the current segment is a fixed boundary
        if end in fixed_boundaries:
            is_boundary = True
        else:
            # try to see if the next image is similar
            if (end - start) > 3 and end not in blurred:
                sim_to_anchor = features[start] @ features[end].T
                sim = all_sims[end - 1] + sim_to_anchor
                sim = sim / 2
                if sim < threshold:
                    is_boundary = True

        # check if the segment is too long
        if end - start > 1000:
            is_boundary = True

        if is_boundary:
            segments.append((start, end + 1))
            start = end + 1
            end = start + 1
            continue
        end += 1

    if len(photo_ids) > 0 and start < len(photo_ids):
        segments.append((start, len(photo_ids)))

    # double check that all indices are in the segments
    all_indices = set(range(len(photo_ids)))
    all_used_indices = set()
    for start, end in segments:
        all_used_indices.update(set(range(start, end)))

    if all_indices != all_used_indices:
        rprint(f"[red]Warning: Not all indices are used in segments for {data}.[/red]")
        print(
            f"Used indices: {len(all_used_indices)}, Total indices: {len(all_indices)}"
        )
        unused_indices = all_indices - all_used_indices
        print(f"Unused indices: {len(unused_indices)}")

    return segments


OVERWRITE_SEGMENTS = False  # Set to True to overwrite existing segments
OVERWRITE = [Data.CASTLE]


def load_segments(
    data: Data,
) -> Tuple[List[Tuple[int, int]], List[List[str]], Dict[str, int], List[str]]:
    print(f"Loading segments for {data}...")
    if data == Data.LSC23:
        path = f"{CLIP_EMBEDDINGS}/{data}/google-siglip-so400m-patch14-384_nonorm"
    else:
        path = f"{CLIP_EMBEDDINGS}/{data}/siglip-so400m-patch14-384"
    # else:
    #     path = f"{CLIP_EMBEDDINGS}/{data}/blip2_lavis"
    photo_ids = pd.read_csv(f"{path}/photo_ids.csv")["photo_id"].tolist()

    segment_path = f"{DATA_DIRECTORY}/{data}_segments.json"
    to_overwrite = OVERWRITE_SEGMENTS and data in OVERWRITE
    if not to_overwrite and os.path.exists(segment_path):
        segments = json.load(open(f"{DATA_DIRECTORY}/{data}_segments.json"))
    else:
        segments = create_new_segments(
            data, photo_ids, np.load(f"{path}/features.npy"), blurred_indices[data]
        )
        # save segments to file
        with open(segment_path, "w") as f:
            json.dump(segments, f)

    # segments = [(segment[0], segment[1]) for segment in segments]
    rprint(f"[green]Found {len(segments)} segments for {data}.[/green]")
    average_length = np.mean([end - start for start, end in segments])
    rprint(f"[green]Average segment length: {average_length:.2f} photos.[/green]")

    segment_photos = []
    photo_to_segment_id = {}
    used = set()
    print("Last segment:", segments[-1])
    for segment_id, (start, end) in enumerate(segments):
        segment_photos.append(photo_ids[start:end])
        for photo_id in photo_ids[start:end]:
            photo_to_segment_id[photo_id] = segment_id
            used.add(photo_id)

    # Check if all photo_ids are used
    all_photo_ids = set(photo_ids)
    if all_photo_ids != used:
        rprint(
            f"[orange]Warning: Not all photo IDs are used in segments for {data}.[/orange]"
        )
        unused_photos = all_photo_ids - used
        print(f"Unused photo IDs: {len(unused_photos)}")

    return segments, segment_photos, photo_to_segment_id, photo_ids


class PreSegments:
    def __init__(self, data: Data):
        self.data = data
        self.segments, self.segment_photos, self.photo_to_segment_id, self.photo_ids = load_segments(data)
        self.all_events = []

    @property
    def events(self) -> List[Event]:
        """
        Load events only if they are not already loaded.
        """
        if not self.all_events:
            batch_size = 5000
            for i in tqdm.tqdm(
                range(0, len(self.segments), batch_size),
                desc=f"Loading events for {self.data}",
            ):
                segment_batch = self.segments[i : i + batch_size]
                self.all_events.extend(segments_to_events(self.data, segment_batch, None, self.photo_ids))
        return self.all_events


presegments = {
    Data.LSC23: PreSegments(Data.LSC23),
    Data.Deakin: PreSegments(Data.Deakin),
    Data.CASTLE: PreSegments(Data.CASTLE),
}


def get_segments_from_top_photos(
    top_photos: List[str],
    scores: List[float],
    data: Data,
    size: int = DEFAULT_SIZE,
) -> Tuple[List[Tuple[int, int]], List[List[str]], List[float]]:
    segments = presegments[data].segments
    photo_to_segment_id = presegments[data].photo_to_segment_id

    photo_ids = SIGLIP_FEATURES[data].ids
    blurred = blurred_indices[data]

    done = set()
    segment_photos = []
    segment_scores = []
    valid_segments = []

    for photo_id, score in zip(top_photos, scores):
        # get the segment for the photo_id
        segment_id = photo_to_segment_id.get(photo_id, None)
        if segment_id is None:
            print(f"Photo ID {photo_id} not found in photo_to_segment_id, skipping.")
            continue
        if segment_id in done:
            continue
        try:
            segment = segments[segment_id]
            valid_segments.append(segment)
            segment_photos.append(
                [
                    photo_ids[photo]
                    for photo in range(segment[0], segment[1])
                    if photo not in blurred
                ]
            )
            segment_scores.append(score)
            done.add(segment_id)
        except (KeyError, IndexError):
            print(f"Photo ID {photo_id} not found in segments, skipping.")
            continue

        if len(valid_segments) >= size:
            break

    return valid_segments, segment_photos, segment_scores


@timer("merge_results")
def merge_results(
    all_scores,
    top_segment_ids,
    top_scores,
    photo_ids,
    segments,
    allow_none=True,
    events: List[Event] = [],
) -> Tuple[List[List[List[str]]], List[float]]:
    print(f"Merging results for {len(top_segment_ids)} top segments...")
    num_queries = len(all_scores)
    photo_to_segment_id = presegments[Data.LSC23].photo_to_segment_id

    # Step 2: Group overlapping combinations
    merged_groups = []
    used = set()
    to_check = "201905/12/20190512_050408_000.jpg"
    to_check_id = photo_ids.index(to_check) if to_check in photo_ids else None
    seg_to_check = photo_to_segment_id.get(to_check, None)
    to_check_2 = "201905/11/20190511_180100_000.jpg"
    to_check_2_id = photo_ids.index(to_check_2) if to_check_2 in photo_ids else None
    seg_to_check_2 = photo_to_segment_id.get(to_check_2, None)

    print("--" * 20)
    print("All segments to check for", seg_to_check, seg_to_check_2)
    to_checks = []
    for i, combo in enumerate(top_segment_ids):
        if seg_to_check is not None and seg_to_check in combo:
            print(f"Segment {i} contains {to_check} ({to_check_id}). Segment: {combo}")
            to_checks.append(i)
        if seg_to_check_2 is not None and seg_to_check_2 in combo:
            print(
                f"Segment {i} contains {to_check_2} ({to_check_2_id}). Segment: {combo}"
            )
            to_checks.append(i)

    print("--" * 20)
    print(
        f"Checking for overlaps with {to_check} ({to_check_id}) and {to_check_2} ({to_check_2_id})"
    )
    for i, combo in enumerate(top_segment_ids):
        if i in used:
            continue
        group = [i]
        used.add(i)
        for j in range(i + 1, len(top_segment_ids)):
            if j in used:
                continue

            overlap_found = False
            for s1, s2 in zip(combo, top_segment_ids[j]):
                if s1 is None or s2 is None:
                    continue
                start1, end1 = segments[s1]
                start2, end2 = segments[s2]
                # event1 = events[s1] if s1 < len(events) else None
                # event2 = events[s2] if s2 < len(events) else None

                # if event1 is None or event2 is None:
                #     continue

                # if event1.location != event2.location:
                #     continue

                # if event1.start_time.date() != event2.start_time.date():
                #     continue

                # if to_check_id is not None and (
                #     start1 <= to_check_id < end1 or
                #     start2 <= to_check_id < end2
                # ):
                #     print("???")
                #     print(combo, top_segment_ids[j])

                if not (end1 <= start2 or end2 <= start1):
                    overlap_found = True
                    break

            if overlap_found:
                # If they are, we can merge them
                group.append(j)
                used.add(j)

        merged_groups.append(group)

    # Step 3: Collect segment IDs and photo IDs per query
    merged_results = []  # List of N-length lists of photo IDs per query
    merged_scores = []  # List of scores for each merged group

    all_scores = np.array(all_scores)
    for group in merged_groups:
        per_query_segments = [[] for _ in range(num_queries)]

        # Accumulate segment IDs per query, skipping None
        for idx in group:
            combo = top_segment_ids[idx]
            for q in range(num_queries):
                seg_id = combo[q]
                if seg_id is not None:
                    per_query_segments[q].append(seg_id)

        # Deduplicate and sort by time
        for q in range(num_queries):
            per_query_segments[q] = sorted(
                set(per_query_segments[q]), key=lambda sid: segments[sid][0]
            )

        # Convert segment IDs to photo IDs
        per_query_photos = []
        for q in range(num_queries):
            seg_ids = per_query_segments[q]
            photos = [photo_ids[i] for seg in seg_ids for i in range(*segments[seg])]
            per_query_photos.append(photos)

        if not allow_none and any(len(photos) == 0 for photos in per_query_photos):
            continue

        merged_results.append(per_query_photos)
        merged_scores.append(np.max([top_scores[idx] for idx in group]))

    # Step 4: Sort merged results by score
    sorted_indices = np.argsort(-np.array(merged_scores))
    merged_results = [merged_results[i] for i in sorted_indices]
    merged_scores = [merged_scores[i] for i in sorted_indices]

    print(f"Merged into {len(merged_results)} groups.")
    return merged_results, merged_scores


I = TypeVar("I", Image, str)


def restart_ssh_tunnel():
    """
    Restart the SSH tunnel to the Deakin server.
    This is a placeholder function that should be implemented
    with the actual logic to restart the SSH tunnel.
    """
    print("Restarting SSH tunnel...")
    # Implement the logic to restart the SSH tunnel here
    # For example, using subprocess to run an SSH command
    subprocess.run(
        ["ssh", "-f", "-N", "-L", "8080:localhost:8080", "tranl@AdaptCluster"],
        check=True,
    )
    print("SSH tunnel restarted.")


def send_deakin_rerank_request(
    image_files: List[str],
    instruction: str = "Is anyone eating or drinking?",
):
    api = "http://localhost:8080/predict"
    # image_files = [
    #     os.path.join(IMAGE_DIRECTORY, "Deakin", image_file)
    #     for image_file in image_files
    # ]
    # files = [("data", (open(img_path, "rb"))) for img_path in image_files]
    # response = requests.post(api, files=files, data={"instruction": instruction, "return_description": False})
    response = requests.post(
        api,
        json={
            "return_description": False,
            "images": image_files,
        },
    )
    if response.status_code == 403:
        print("SSH tunnel might be down, restarting...")
        restart_ssh_tunnel()
        response = requests.post(
            api,
            json={
                "return_description": False,
                "images": image_files,
            },
        )
    if response.status_code != 200:
        print(response.text)
        raise Exception(f"Request failed with status code {response.status_code}")
    response_data = response.json()

    return {
        "caption": response_data.get("caption", ""),
        "is_eating": response_data.get("conclusion", "") == "YES",
        "score": response_data.get("score", 0.0),
    }


def get_keyframes_from_segments(
    encoded_query: np.ndarray | None, data: Data, images: List[I]
) -> List[I]:
    # for each segment, use dbscan to cluster the images
    # for each cluster, get the average score
    # for each cluster, get the image with the closest score to the average score and the highest to others average scores
    # return the list of images
    photo_ids = SIGLIP_FEATURES[data].ids
    features = SIGLIP_FEATURES[data].embeddings
    low_density_indices = blurred_indices[data]

    max_num = 4

    if len(images) <= max_num:
        return images

    image_src_to_image: dict[str, I] = {}
    image_srcs: list[str] = []
    for image in images:
        if isinstance(image, Image):
            image_src_to_image[image.src] = image
            image_srcs.append(image.src)
        else:
            image_src_to_image[image] = image
            image_srcs.append(image)

    image_set = set(image_srcs)

    # Get the segment images that are not in the low density indices
    segment_ids = [i for i, image in enumerate(photo_ids) if image in image_set]
    segment_ids = [i for i in segment_ids if i not in low_density_indices]
    good_images = [image_src_to_image[photo_ids[i]] for i in segment_ids]

    if len(good_images) < max_num:
        return good_images

    segment_features = features[np.array(segment_ids)]

    # cluster the images
    dbscan = KMeans(
        n_clusters=min(len(good_images), max_num),
        init="k-means++",
        random_state=42,
        n_init="auto",
    )
    clusters = dbscan.fit_predict(segment_features)

    chunk = []
    for cluster in set(clusters):
        cluster_images = [
            image for i, image in enumerate(good_images) if clusters[i] == cluster
        ]
        cluster_set = set()
        for image in cluster_images:
            if isinstance(image, Image):
                cluster_set.add(image.src)
            else:
                cluster_set.add(image)

        if len(cluster_images) == 1:
            chunk.append(cluster_images[0])
        else:
            cluster_ids = [
                i for i, image in enumerate(photo_ids) if image in cluster_set
            ]
            cluster_features = features[np.array(cluster_ids)]
            cluster_feat = np.mean(cluster_features, axis=0)
            cluster_feat = cluster_feat / np.linalg.norm(cluster_feat)

            distinct_scores = cluster_features @ cluster_feat.T
            if encoded_query is not None:
                image_scores = cluster_features @ encoded_query.T
                distinct_scores += image_scores
            closest_image = cluster_images[np.argmax(distinct_scores)]
            chunk.append(closest_image)

    # sort the images by the order they appear in the segment
    chunk = sorted(
        chunk, key=lambda x: image_srcs.index(x if isinstance(x, str) else x.src)
    )
    return chunk


lambda1 = 0.5
lambda2 = 1 - lambda1


def expand_single_image(
    data: Data,
    query: str,
    seed: str,
    start: str,
    end: str,
):
    """
    Find a segment of images that are similar to the seed image,
    starting from the start image and ending at the end image.
    The segment is expanded left and right from the seed image,
    until the similarity drops below a threshold.
    """
    # Expand left and right from the seed, with fixed boundaries
    model = get_model(data)
    photo_ids = model.photo_ids(data)
    seed_index = photo_ids.index(seed)
    start_index = max(photo_ids.index(start), 0)
    end_index = min(photo_ids.index(end), len(photo_ids) - 1)

    photo_feat = model.photo_features(data)[seed_index]

    # Expand left and right
    left = 0
    right = 0
    while seed_index - left > start_index:
        left_feat = model.photo_features(data)[seed_index - left]
        sim = photo_feat @ left_feat.T
        if sim < 0.9:
            break
        left += 1
        photo_feat = left_feat

    photo_feat = model.photo_features(data)[seed_index]
    while seed_index + right < end_index:
        right_feat = model.photo_features(data)[seed_index + right]
        sim = photo_feat @ right_feat.T
        if sim < 0.9:
            break
        right += 1
        photo_feat = right_feat

    return photo_ids[seed_index - left], photo_ids[seed_index + right]
