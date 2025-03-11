import time
from collections.abc import Set
from typing import Optional

import numpy as np
import pandas as pd
from configs import CLIP_EMBEDDINGS
from database.main import get_db, image_collection
from query_parse.types.requests import Data
from query_parse.visual import clip_model, clipa_model, get_model, photo_ids
from tqdm.auto import tqdm

from retrieval.async_utils import timer
from retrieval.rerank import reranker


def get_blurred_indices(data: Data):
    blurred_df = pd.read_csv(f"{CLIP_EMBEDDINGS}/{data}/blurred.csv")
    blurred_df["laplacian_var"] = blurred_df["laplacian_var"].fillna(0)
    blurred_images = blurred_df[blurred_df["laplacian_var"] < 10]["image"].tolist()
    blurred_images = set(blurred_images)
    blurred_indices = [
        i for i, image in enumerate(photo_ids(data)) if image in blurred_images
    ]
    return set(blurred_indices)

def get_low_visual_density_indices(data: Data):
    low_density_df = pd.read_csv(f"{CLIP_EMBEDDINGS}/{data}/visual_density.csv")
    low_density_images = low_density_df[low_density_df["score"] < 5]["image"].tolist()
    low_density_images = set(low_density_images)
    low_density_indices = [
        i for i, image in enumerate(photo_ids(data)) if image in low_density_images
    ]
    return set(low_density_indices)


blurred_indices = {
    Data.LSC23: get_low_visual_density_indices(Data.LSC23),
    Data.Deakin: get_low_visual_density_indices(Data.Deakin),
}

clear_indices = {
    Data.LSC23: set(range(len(photo_ids(Data.LSC23)))) - blurred_indices[Data.LSC23],
    Data.Deakin: set(range(len(photo_ids(Data.Deakin)))) - blurred_indices[Data.Deakin],
}


def detect_noise(scores1, scores2, method="absolute", threshold=None, percentile=95):
    """
    Detect noisy indices based on the difference between two score arrays.

    Parameters:
    - scores1: First array of scores.
    - scores2: Second array of scores.
    - method: "absolute" or "relative".
    - threshold: Fixed threshold for noise detection. If None, use percentile.
    - percentile: Percentile to dynamically compute the threshold if not provided.

    Returns:
    - noisy_indices: Indices where the difference exceeds the threshold.
    - differences: Array of differences.
    """
    # Compute differences
    if method == "absolute":
        differences = np.abs(scores1 - scores2)
    elif method == "relative":
        differences = np.abs(scores1 - scores2) / (
            np.abs(scores1) + 1e-8
        )  # Avoid division by zero
    else:
        raise ValueError(f"Unknown method: {method}")

    # Determine the threshold
    if threshold is None:
        threshold = np.percentile(differences, percentile)

    # Detect noisy indices
    noisy_indices = np.where(differences > threshold)[0]

    return noisy_indices, differences


def estimate_variance_threshold(
    normalized_scores, method="global", scaling_factor=1.5, sample_size=1000
):
    """
    Estimate the variance threshold without computing all possible segment variances.

    Parameters:
    - normalized_scores: Array of normalized scores.
    - method: "global", "sampling", "statistics", "percentile".
    - scaling_factor: Multiplier for variance-based thresholds.
    - sample_size: Number of samples to use for "sampling" method.

    Returns:
    - Estimated variance threshold.
    """
    if method == "global":
        # Use global variance
        global_variance = np.var(normalized_scores)
        return global_variance * scaling_factor

    elif method == "sampling":
        # Randomly sample variances from limited segments
        sampled_indices = np.random.choice(
            len(normalized_scores), sample_size, replace=False
        )
        sampled_variances = [
            np.var(normalized_scores[i : i + 10])
            for i in sampled_indices
            if i + 10 < len(normalized_scores)
        ]
        return np.percentile(sampled_variances, 75)  # Use the 75th percentile

    elif method == "statistics":
        # Estimate based on mean and standard deviation
        std_normalized_scores = np.std(normalized_scores)
        return (std_normalized_scores**2) * scaling_factor

    elif method == "percentile":
        # Estimate based on score distribution percentiles
        spread = np.percentile(normalized_scores, 90) - np.percentile(
            normalized_scores, 10
        )
        return (spread**2) / scaling_factor

    else:
        raise ValueError(f"Unknown method: {method}")


lambda1 = 0.75
lambda2 = 1 - lambda1


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

    return False


def get_fixed_boundaries(data):
    sort_criteria = None
    if data == Data.LSC23:
        sort_criteria = [("utc_time", 1)]
    elif data == Data.Deakin:
        sort_criteria = [("patient.id", 1), ("snap.local_time", 1)]

    boundaries = set()
    prev_image = None
    for image_data in image_collection(get_db(data)).find().sort(sort_criteria):
        if prev_image is not None:
            if compare_images(data, prev_image, image_data):
                try:
                    boundaries.add(photo_ids(data).index(image_data["image"]))
                except ValueError:
                    pass
        prev_image = image_data
    return boundaries


FIXED_BOUNDARIES = {
    Data.LSC23: get_fixed_boundaries(Data.LSC23),
    Data.Deakin: get_fixed_boundaries(Data.Deakin),
}


@timer("get_segments")
def get_segments(
    query: str,
    data: Data = Data.LSC23,
    score_percentile: int = 98,
    variance_percentile: int = 75,
    max_gap: int = 5,
    max_length: int = 100,
    filters: Optional[Set[str]] = None,
    to_merge: bool = False,
    size: int | None = None,
    metadata_scores: dict = {},
):
    print("Query", query)
    good_indices, scores, score_threshold, get_group_score = get_scores(
        data, query, filters, score_percentile, metadata_scores
    )

    if len(good_indices) == 0:
        print("No high-scoring images found.")
        return {
            "segments": [],
            "segment_scores": [],
            "scores": [],
            "high_score_indices": [],
        }

    # Normalize scores for segment scoring
    max_score = np.max(scores)
    normalized_scores = scores / max_score

    # Dynamically determine the variance threshold
    variance_threshold = estimate_variance_threshold(
        normalized_scores=normalized_scores, method="sampling", sample_size=1000
    )
    print(
        f"Dynamic variance threshold (percentile {variance_percentile}): {variance_threshold}"
    )

    def expand_segment(seed, direction):
        """
        Expand the segment starting from a seed index in the given direction.
        - direction: 1 for right, -1 for left
        """
        segment = [seed]
        gap_count = 0
        for step in range(1, max_length):
            next_idx = seed + direction * step

            if direction == 1 and next_idx in FIXED_BOUNDARIES[data]:
                # Stop expanding if fixed boundary is reached
                break

            if direction == -1 and next_idx + 1 in FIXED_BOUNDARIES[data]:
                # Using next_idx + 1 to get the right boundary
                break

            if next_idx < 0 or next_idx >= len(scores):
                break  # Out of bounds

            if scores[next_idx] >= score_threshold or gap_count < max_gap:
                segment.append(next_idx)
                if (
                    scores[next_idx] < score_threshold
                    or next_idx in blurred_indices[data]
                ):
                    gap_count += 1
                else:
                    # Reset gap count if a high-scoring image is encountered
                    gap_count = 0
            else:
                break  # Stop expanding if variance exceeds threshold or max gap is reached

            # Check variance
            segment_scores = normalized_scores[segment]
            if np.var(segment_scores) > variance_threshold:
                segment.pop()  # Remove the last added index
                break

        if direction == -1:
            segment = segment[::-1]  # Reverse the segment
        return segment

    segments = []
    used_indices = set()

    # sort the good indices by score
    good_indices = sorted(good_indices, key=lambda x: scores[x], reverse=True)
    hits = set()
    for seed in tqdm(good_indices):
        if seed in used_indices:
            continue  # Skip seeds already covered in a segment

        # Expand left and right
        left_segment = expand_segment(seed, direction=-1)
        right_segment = expand_segment(seed, direction=1)
        full_segment = left_segment + right_segment[1:]  # Skip the seed index

        if len(full_segment) == 0:
            continue

        # Add segment to hits
        hits.update(full_segment)

        # Calculate segment score
        segment_scores = normalized_scores[full_segment]
        segment_length = len(full_segment)
        group_score = get_group_score(full_segment) / max_score
        variance = np.var(segment_scores)
        if segment_length == 1:
            length_reward = 0.0
        elif segment_length >= 50:
            length_reward = 0.05
        else:
            length_reward = 0.05 * np.log(segment_length)  # Example length reward
        segment_score = group_score - variance + length_reward

        # Mark indices as used
        used_indices.update(full_segment)
        segments.append(
            (full_segment, segment_score, group_score, variance, length_reward)
        )

    # Merge overlapping segments
    if not to_merge:
        merged_segments = segments
    else:
        # sorted segments by start index
        segments.sort(key=lambda x: x[0][0])
        merged_segments = []
        i = 0
        while i < len(segments):
            segment = segments[i]
            start, end = segment[0][0], segment[0][-1]
            seg_score, group_score, variance, length_reward = (
                segment[1],
                segment[2],
                segment[3],
                segment[4],
            )
            j = i + 1
            while j < len(segments):
                next_segment = segments[j]
                next_start, next_end = next_segment[0][0], next_segment[0][-1]
                next_seg_score, _, next_variance, next_length_reward = (
                    next_segment[1],
                    next_segment[2],
                    next_segment[3],
                    next_segment[4],
                )
                if next_start <= end:
                    # Overlapping segments
                    end = max(end, next_end)
                    seg_score += next_seg_score
                    group_score = get_group_score(range(start, end + 1)) / max_score
                    variance += next_variance
                    length_reward += next_length_reward
                    j += 1
                else:
                    break

            merged_segments.append(
                ([start, end], seg_score, group_score, variance, length_reward)
            )
            i = j

    # Sort segments by score
    merged_segments.sort(key=lambda x: x[1], reverse=True)

    # Convert segment indices back to ranges
    result_segments = []
    result_scores = []
    # i = 0
    for segment, seg_score, group_score, variance, length_reward in merged_segments:
        start, end = segment[0], segment[-1]
        result_segments.append((start, end + 1))  # Include end index
        result_scores.append(seg_score)
        # i += 1
        # if i <= 10:
        # print(f"Segment {i}: Start: {start}, End: {end}, Length: {end - start + 1}")
        # print(
        #     f"Segment score: {seg_score:0.2f}, Group score: {group_score:0.2f}, Variance: {variance:0.2f}, Length reward: {length_reward:0.2f}"
        # )

    return {
        "segments": result_segments,
        "segment_scores": result_scores,
        "scores": scores,
        "high_score_indices": hits,
    }


def get_scores(data: Data, query: str, filters: Optional[Set[str]], score_percentile: int, metadata_scores: dict[str, float]):
    main_model = get_model(data)
    now = time.time()

    scores, encoded_query = main_model.score_all_images(query, data)
    photo_ids = main_model.photo_ids[data]
    print(f"--> Score calculation time 1: {time.time() - now:.2f} seconds")
    now = time.time()

    alt_model = clip_model if data == Data.LSC23 else clipa_model
    alt_scores, alt_encoded_query = alt_model.score_all_images(query, data)
    print(f"--> Score calculation time 2: {time.time() - now:.2f} seconds")
    now = time.time()

    # Add metadata scores
    np_metadata_scores = np.array([metadata_scores.get(photo_id, 0) for photo_id in photo_ids])
    metadata_scores = np_metadata_scores / np.max(np_metadata_scores)

    scores = (
        np.array(scores) * lambda1 + np.array(alt_scores) * lambda2 # + np_metadata_scores * 0.1
    )  # Vectorized combination

    print(f"--> Score calculation time: {time.time() - now:.2f} seconds")
    now = time.time()

    def get_group_score(segment):
        main_score = main_model.norm_photo_features[data][segment] @ encoded_query.T
        alt_score = alt_model.norm_photo_features[data][segment] @ alt_encoded_query.T
        return np.mean(lambda1 * main_score + lambda2 * alt_score)

    # Filter out blurred images
    good_indices = clear_indices[data]
    # Filter out images that do not match the filters
    if filters:
        filter_indices = set(i for i, image in enumerate(photo_ids) if image in filters)
        good_indices = good_indices.intersection(filter_indices)

    # Dynamically determine the score threshold
    okay_scores = [scores[i] for i in good_indices]
    score_threshold = np.percentile(okay_scores, score_percentile)
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
    chosen_model = get_model(data)
    photo_ids = chosen_model.photo_ids[data]
    seed_index = photo_ids.index(seed)
    start_index = max(photo_ids.index(start), 0)
    end_index = min(photo_ids.index(end), len(photo_ids) - 1)

    photo_feat = chosen_model.norm_photo_features[data][seed_index]

    # Expand left and right
    left = 0
    right = 0
    while seed_index - left > start_index:
        left_feat = chosen_model.norm_photo_features[data][seed_index - left]
        sim = photo_feat @ left_feat.T
        if sim < 0.9:
            break
        left += 1
        photo_feat = left_feat

    photo_feat = chosen_model.norm_photo_features[data][seed_index]
    while seed_index + right < end_index:
        right_feat = chosen_model.norm_photo_features[data][seed_index + right]
        sim = photo_feat @ right_feat.T
        if sim < 0.9:
            break
        right += 1
        photo_feat = right_feat

    return photo_ids[seed_index - left], photo_ids[seed_index + right]


@timer("get_segments_2")
def get_segments_2(
    query: str,
    data: Data = Data.LSC23,
    filters: Optional[Set[str]] = None,
):
    print("Query", query)
    chosen_model = get_model(data)
    alternative_model = clip_model if data == Data.LSC23 else clipa_model

    photo_ids = get_model(data).photo_ids[data]
    features = chosen_model.norm_photo_features[data]
    alt_features = alternative_model.norm_photo_features[data]

    filtered_indices = [i for i, image in enumerate(photo_ids) if image in filters]
    filtered_features = features[np.array(filtered_indices)]

    all_scores, _ = chosen_model.score_all_images(query, data)
    alt_scores, _ = alternative_model.score_all_images(query, data)

    all_scores = np.array(all_scores)
    alt_scores = np.array(alt_scores)
    all_scores = lambda1 * all_scores + lambda2 * alt_scores

    all_sims = []
    for i in range(len(filtered_indices) - 1):
        j = i + 1
        sim = filtered_features[i] @ filtered_features[j].T
        all_sims.append(sim)

    # lower threshold means bigger segments
    threshold = np.percentile(all_sims, 90)
    # lower score threshold means more segments
    score_threshold = np.percentile(all_scores, 98)
    lower_score_threshold = np.percentile(all_scores, 70)
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
        if all_sims[end - 1] < threshold and end - start > 5:
            segments.append((filtered_indices[start], filtered_indices[end] + 1))
            start = end + 1
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

    checking_image="ID137/2022/06/27/ID137_20220627_173512_000.jpg"
    print("Checking", checking_image)
    for i, (start, end) in enumerate(segments):
        if checking_image in photo_ids[start:end]:
            print("Found in segment", i)
            print("Segment scores", all_scores[start:end])
            break

    print("Number of segments", len(segments))
    print("Segment Lengths", [end - start for start, end in segments])

    # rerank segments
    results = []
    scores = []
    hits = []
    print("Reranking segments")
    for start, end in tqdm(segments):
        images = [f"Deakin/{photo_ids[i]}" for i in range(start, end)]
        if len(images) > 8:
            # get the top 16 images
            image_scores = all_scores[start:end]
            image_indices = np.argsort(image_scores)[::-1][:8]
            images = [images[i] for i in image_indices]

        # mean_score = np.mean(features[start:end] @ encoded_query.T)
        max_score = max(all_scores[start:end])

        results += [(start, end)]
        okay = False
        score = max_score
        if max_score > score_threshold:
            okay = True
        elif max_score > lower_score_threshold:
            score = reranker.score(query, images)
            if score > 0.5:
                print("Reranked", score)
                okay = True

        if okay:
            scores.append(max_score)
            hits.append(True)
        else:
            scores.append(-1)
            hits.append(False)

    print(f"Filtered {len(segments)} segments to {len([s for s in scores if s > -1])} segments")
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

                            feat1 = alt_features[start:end]
                            feat2 = alt_features[next_start:next_end]
                            feat1 = np.mean(feat1, axis=0)
                            feat2 = np.mean(feat2, axis=0)
                            sim = feat1 @ feat2.T

                            score = lambda1 * score + lambda2 * sim

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
    return {
        "segments": results,
        "segment_scores": scores,
        "scores": scores,
        "high_score_indices": [],
    }

# query = "I am having food or interacting with food"
# results = get_segments(query=query, data=Data.Deakin, max_gap=5)
# segments = results["segments"]
# print("Number of segments", len(segments))
# images = []
# deakin_photo_ids = photo_ids(Data.Deakin)
# for start, end in segments:
#     images.append(deakin_photo_ids[start:end])
# with open("segments.txt", "w") as f:
#     for image_list in images:
#         f.write(", ".join(image_list))
#         f.write("\n")
