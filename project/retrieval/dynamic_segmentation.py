import os
import time
from collections.abc import Set
from typing import List, Optional, TypeVar

import numpy as np
import requests
from configs import IMAGE_DIRECTORY
from query_parse.types.requests import Data
from results.models import Image
from sklearn.cluster import KMeans
from tqdm.auto import tqdm
from visual.features import SIGLIP_FEATURES
from visual.low_visual import blurred_indices, clear_indices
from visual.main import get_model, get_model_by_name

from retrieval.async_utils import timer
from retrieval.graph_utils import get_heatmap_from_images
from retrieval.rerank import reranker

I = TypeVar("I", Image, str)


def send_deakin_rerank_request(
    image_files: List[str],
    instruction: str = "Is anyone eating or drinking?",
):
    api = "http://localhost:8081/predict"
    image_files = [
        os.path.join(IMAGE_DIRECTORY, "Deakin", image_file)
        for image_file in image_files
    ]
    files = [("data", (open(img_path, "rb"))) for img_path in image_files]
    response = requests.post(api, files=files, data={"instruction": instruction})
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}")
    response_data = response.json()

    return {
        "caption": response_data.get("caption", ""),
        "is_eating": response_data.get("conclusion", "") == "YES",
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


def get_scores(
    data: Data,
    query: str,
    filters: Optional[Set[str]],
    score_percentile: int,
    metadata_scores: dict[str, float],
):
    main_model = get_model(data)
    now = time.time()

    scores, encoded_query = main_model.score_all_images(query, data)
    photo_ids = main_model.photo_ids(data)
    print(f"--> Score calculation time 1: {time.time() - now:.2f} seconds")
    now = time.time()

    alt_model = None
    alt_encoded_query = None
    if data == Data.LSC23:
        alt_model = get_model_by_name("clip")
        alt_scores, alt_encoded_query = alt_model.score_all_images(query, data)
        print(f"--> Score calculation time 2: {time.time() - now:.2f} seconds")
        now = time.time()
        scores = (
            np.array(scores) * lambda1
            + np.array(alt_scores) * lambda2  # + np_metadata_scores * 0.1
        )  # Vectorized combination
    else:
        scores = np.array(scores)

    # Add metadata scores
    np_metadata_scores = np.array(
        [metadata_scores.get(photo_id, 0) for photo_id in photo_ids]
    )
    max_metadata_score = np.max(np_metadata_scores)
    if max_metadata_score > 0:
        metadata_scores = np_metadata_scores / max_metadata_score

    print(f"--> Score calculation time: {time.time() - now:.2f} seconds")
    now = time.time()

    def get_group_score(segment):
        main_score = main_model.features[data].embeddings[segment] @ encoded_query.T
        if alt_model is None or alt_encoded_query is None:
            return np.mean(main_score)
        alt_score = alt_model.features[data].embeddings[segment] @ alt_encoded_query.T
        return np.mean(lambda1 * main_score + lambda2 * alt_score)

    # Filter out blurred images
    good_indices = clear_indices[data]
    # Filter out images that do not match the filters
    if filters:
        filter_indices = set(i for i, image in enumerate(photo_ids) if image in filters)
        good_indices = good_indices.intersection(filter_indices)

    # score_threshold = np.percentile(okay_scores, score_percentile)
    score_threshold = 0.0403
    print(f"Dynamic score threshold (percentile {score_percentile}): {score_threshold}")
    now = time.time()

    # Filter high-scoring images
    high_score_indices = np.where(scores > score_threshold)[0]
    now = time.time()
    good_indices = good_indices.intersection(set(high_score_indices))

    # Keep only filtered indices
    print(f"Found {len(good_indices)} high-scoring images.")
    now = time.time()
    return good_indices, scores, score_threshold, get_group_score


def expand_single_image(
    data: Data,
    query: str,
    seed: str,
    start: str,
    end: str,
):
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


@timer("get_segments_2")
def get_segments_related_to_text(
    query: str,
    data: Data = Data.LSC23,
    filters: Optional[Set[str]] = None,
):
    chosen_model = get_model(data)

    photo_ids = SIGLIP_FEATURES[data].ids
    features = SIGLIP_FEATURES[data].embeddings

    if filters is not None:
        filtered_indices = [i for i, image in enumerate(photo_ids) if image in filters]
        filtered_features = features[np.array(filtered_indices)]
    else:
        filtered_indices = list(range(len(photo_ids)))
        filtered_features = features

    all_scores, encoded_query = chosen_model.score_all_images(query, data)
    # encoded_query = chosen_model.encode_text(query)
    # all_scores = get_similarities(data, encoded_query)

    all_scores = np.array(all_scores)
    all_sims = []
    for i in range(len(filtered_indices) - 1):
        j = i + 1
        sim = filtered_features[i] @ filtered_features[j].T
        all_sims.append(sim)

    # lower threshold means bigger segments
    threshold = np.percentile(all_sims, 90)
    # lower score threshold means more eating segments
    score_threshold = np.percentile(all_scores, 97)
    lower_score_threshold = np.percentile(all_scores, 80)
    print("Threshold", threshold)
    print("Score Threshold", score_threshold)

    # Filter out blurred images
    blurred = blurred_indices[data]
    blurred_array = np.array([i in blurred for i in range(len(photo_ids))])
    all_scores[blurred_array] = -1

    # Get segments from left to right
    segments = []
    start = 0
    end = 1
    while end < len(filtered_indices) and start < len(filtered_indices):
        # try to see if the next image is similar
        if (end - start) > 3 and end not in blurred:
            sim_to_anchor = filtered_features[start] @ filtered_features[end].T
            sim = all_sims[end - 1] + sim_to_anchor
            sim = sim / 2
            if sim < threshold:
                # if the next image is not similar, then we have a segment
                segments.append(
                    (filtered_indices[start], filtered_indices[end - 1] + 1)
                )
                start = end
                end = start + 1
                continue
        end += 1

    if len(filtered_indices) > 0 and start < len(filtered_indices):
        segments.append((filtered_indices[start], filtered_indices[-1] + 1))

    # double check that all indices are in the segments
    all_indices = set(filtered_indices)
    all_used_indices = set()
    for start, end in segments:
        all_used_indices.update(set(range(start, end)))

    assert all_indices == all_used_indices, "Not all indices are used " + str(
        all_indices - all_used_indices
    )

    # rerank segments
    results = []
    scores = []
    hits = []
    print("Reranking segments")
    for start, end in tqdm(segments):
        images = [photo_ids[i] for i in range(start, end)]

        # mean_score = np.mean(features[start:end] @ encoded_query.T)
        max_score = max(all_scores[start:end])
        results += [(start, end)]
        okay = False
        score = max_score
        if max_score > score_threshold:
            okay = True
        elif max_score > lower_score_threshold:
            keyframes = get_keyframes_from_segments(encoded_query, data, images)
            print("Keyframes", keyframes)
            score = reranker.score(
                data,
                query,
                keyframes,
                prompt="Is this segment related to eating? Answer with True or False.",
                tokens=["True", "False"],
            )
            if score > 0.5:
                print("Reranked", score)
                okay = True
            else:
                rerank = send_deakin_rerank_request(
                    keyframes,
                    instruction="Is anyone eating or drinking?",
                )
                print("Deakin rerank", rerank)
                if rerank["is_eating"]:
                    okay = True
                    score = max_score * 2

        if okay:
            scores.append(max_score)
            hits.append(True)
        else:
            scores.append(-1)
            hits.append(False)

    print(
        f"Filtered {len(segments)} segments to {len([s for s in scores if s > -1])} segments"
    )
    assert len(results) == len(scores)

    # merge consecutive segments that have the same category
    to_merge = True
    if to_merge:
        merged_segments = []
        merged_scores = []
        merged_hits = []
        i = 0
        current_scores = []
        while i < len(results):
            start, end = results[i]
            current_scores = [scores[i]]
            j = i + 1
            while j < len(results):
                next_start, next_end = results[j]
                if hits[i] == hits[j]:
                    end = next_end
                    current_scores.append(scores[j])
                else:
                    if hits[j]:
                        # 0 - 1
                        break
                    else:
                        # 1 - 0
                        okay = False
                        if next_end - next_start < 3:
                            # if the segment is too small, then it is okay to merge
                            okay = True
                        else:
                            feat1 = features[start:end]
                            feat2 = features[next_start:next_end]
                            feat1 = np.mean(feat1, axis=0)
                            feat2 = np.mean(feat2, axis=0)
                            score = feat1 @ feat2.T
                            if score > threshold:
                                okay = True

                        if okay:
                            end = next_end
                            current_scores.append(scores[j])

                        # don't merge too many segments
                        break
                j += 1

            merged_segments.append((start, end))
            merged_scores.append(max(current_scores))
            merged_hits.append(hits[i])
            i = j

        results = merged_segments
        scores = merged_scores
        hits = merged_hits
        print(f"Merged to {len([i for i in hits if i])} segments")

    # Filter out segments that are not high scoring
    idx = [i for i, hit in enumerate(hits) if hit]
    results = [results[i] for i in idx]
    scores = [scores[i] for i in idx]

    # print(f"Reranked to {len(new_results)} segments")
    filtered_indices = sorted(filtered_indices)

    heatmap = get_heatmap_from_images(
        images=[photo_ids[i] for i in filtered_indices],
        scores=[all_scores[i] for i in filtered_indices],
    )

    return {
        "segments": results,
        "segment_scores": scores,
        "scores": all_scores,
        "heatmap": heatmap,
        "high_score_indices": [],
    }
