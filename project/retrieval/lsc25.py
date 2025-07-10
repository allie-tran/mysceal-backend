from bisect import bisect_left, bisect_right
from typing import List, Optional, Sequence, Set, Tuple

import numpy as np
from configs import WINDOW_SIZE
from database.utils import segment_to_event, segments_to_events
from pydantic import BaseModel
from query_parse.types.lifelog import ParsedQuery, RelevantFields, SingleQuery
from query_parse.types.requests import Data
from results.models import TripletEvent, TripletEventResults
from results.utils import merge_events
from visual.features import SIGLIP_FEATURES
from visual.main import THRESHOLD, ClipModel, get_model, get_model_by_name
from visual.low_visual import blurred
from visual.segments import (
    get_segments_from_top_photos,
    merge_results,
    presegments,
    send_deakin_rerank_request,
)
from visual.types import Array1D

from retrieval.async_utils import async_timer, timer
from retrieval.graph_utils import get_heatmap_from_images


class SegmentResult(BaseModel):
    segments: List[Tuple[int, int]]  # List of (start, end) tuples for segments
    segment_scores: List[float]
    scores: List[float]
    high_score_indices: List[int]
    events: List[TripletEvent]


@async_timer("lsc25_get_segments")
async def lsc25_get_segments(
    query: SingleQuery,
    data: Data = Data.LSC23,
    score_percentile: int = 99,
    include_only: set[str] | None = None,
    # metadata_scores: dict = {},
    top_n: int = 100,
) -> SegmentResult:
    model = get_model(data)
    similarities = await get_lsc25_scores(model, query, include_only, data)

    # np_metadata_scores = np.array(
    #     [metadata_scores.get(photo_id, 0) for photo_id in SIGLIP_FEATURES[data].ids]
    # )
    # max_metadata_score = np.max(np_metadata_scores)
    # if max_metadata_score > 0:
    #     metadata_scores = np_metadata_scores / max_metadata_score
    #     similarities = similarities * metadata_scores

    return get_segments_from_similarity_scores(
        similarities, score_percentile, top_n, data
    )


def get_segments_from_similarity_scores(
    similarities: Array1D,
    score_percentile: float = 95,
    top_n: int = 100,
    data: Data = Data.LSC23,
) -> SegmentResult:
    threshold = np.percentile(similarities, score_percentile)
    threshold = max(threshold, 0.00)  # Ensure threshold is not too low
    high_score_indices = np.where(similarities > threshold)[0].tolist()

    top_indices = np.argsort(similarities)[::-1][:top_n]
    top_photos = [SIGLIP_FEATURES[data].ids[i] for i in top_indices]
    top_similarities = similarities[top_indices]

    segments, segment_photos, segment_scores = get_segments_from_top_photos(
        top_photos, top_similarities.tolist(), data
    )

    events = segments_to_events(
        data,
        segment_photos,
        segment_scores,
        SIGLIP_FEATURES[data].ids,
    )

    if data == Data.LSC23:
        merged_events = merge_events(
            "",
            data,
            TripletEventResults(
                events=[TripletEvent(main=event) for event in events],
                scores=segment_scores,
            ),
            RelevantFields(merge_by=["location"]),
        )
    else:
        merged_events = TripletEventResults(
            events=[TripletEvent(main=event) for event in events],
            scores=segment_scores,
        )

    return SegmentResult(
        segments=segments,
        segment_scores=merged_events.scores,
        scores=similarities.tolist(),
        high_score_indices=high_score_indices,
        events=merged_events.events,
    )


async def get_lsc25_scores(
    model: ClipModel,
    query: SingleQuery,
    include_only: Optional[Set[str]] = None,
    data: Data = Data.LSC23,
    visual_only: bool = False,
) -> Array1D:
    exclude: set[int] = (
        {
            i
            for i, image in enumerate(SIGLIP_FEATURES[data].ids)
            if image not in include_only
        }
        if include_only
        else set()
    )

    similarities = await model.get_lsc25_similarities(
        data,
        query,
        exclude=exclude,
        visual_only=visual_only,
    )
    return similarities


def get_all_segment_scores_from_scores(
    scores: List[float], data: Data = Data.LSC23
) -> List[float]:

    segments, *_ = presegments[data]
    segment_scores = []
    for segment in segments:
        start, end = segment
        segment_score = np.max(scores[start:end])
        segment_scores.append(segment_score)
    return segment_scores


@timer("generate_valid_combinations")
def generate_valid_combinations(times_selected, max_time_gap=5000):
    num_queries = len(times_selected)
    valid_combos = []

    def recurse(path, depth):
        if depth == num_queries:
            valid_combos.append(tuple(path))
            return
        current_times = times_selected[depth]
        if not current_times:
            return  # skip if no candidates for this query
        prev_time = times_selected[depth - 1][path[-1]] if depth > 0 else -np.inf
        for idx, t in enumerate(current_times):
            if t > prev_time:
                if prev_time != -np.inf and t - prev_time > max_time_gap:
                    break
                recurse(path + [idx], depth + 1)

    recurse([], 0)
    return valid_combos


@timer("sliding_window_combinations_with_main")
def sliding_window_combinations_with_main(
    times_selected,
    scores_selected,
    window_size=WINDOW_SIZE,
    stride=100,
    main_event=0,
    allow_none=True,
):
    num_queries = len(times_selected)

    all_times = sorted({t for ts in times_selected for t in ts})
    min_time = all_times[0]
    max_time = all_times[-1]

    valid_combos = []

    def find_best_combo_in_window(t0, t1) -> Sequence[Optional[int]]:
        best_combo = [None] * num_queries
        best_score = -float("inf")

        def backtrack(q, last_time, path, total_score):
            nonlocal best_combo, best_score
            if q == num_queries:
                if total_score > best_score:
                    best_score = total_score
                    best_combo = path[:]
                return

            times = times_selected[q]
            scores = scores_selected[q]

            i0 = bisect_left(times, t0 + 1)
            i1 = bisect_right(times, t1 - 1)

            for i in range(i0, i1):
                t = times[i]
                s = scores[i]
                if t > last_time:
                    path.append(i)
                    backtrack(q + 1, t, path, total_score + s)
                    path.pop()

        backtrack(0, -float("inf"), [], 0)
        return best_combo

    for t0 in range(min_time, max_time, stride):
        t1 = t0 + window_size
        combo = []
        combo = find_best_combo_in_window(t0, t1)
        if combo:
            if allow_none or all(x is not None for x in combo):
                if main_event is None or combo[main_event] is not None:
                    valid_combos.append(tuple(combo))

    # De-duplicate combinations
    valid_combos = list(set(valid_combos))
    return valid_combos


@async_timer("lsc25_multi_queries")
async def lsc25_multi_queries(
    query: ParsedQuery,
    data: Data = Data.LSC23,
    include_only: Optional[Set[str]] = None,
    window_size: int = WINDOW_SIZE,
    # metadata_scores: dict = {},
    # top_n: int = 100,
):
    model = get_model(data)
    queries = query.queries
    main_event = query.main_event
    segments, *_, segmented_events = presegments[data]
    N = len(queries)

    # Step 1: Get all scores for each query
    similarities = [
        await get_lsc25_scores(
            model, query, include_only, data, visual_only=main_event != i
        )
        for i, query in enumerate(queries)
    ]

    segment_scores = [
        get_all_segment_scores_from_scores(similarities[i].tolist(), data)
        for i in range(N)
    ]

    # Step 2: Select top candidates based on percentiles, max 2000
    candidates = []  # list of list of segment indices
    scores_selected = []
    for scores in segment_scores:
        # Get the top 2000 scores
        sorted_indices = np.argsort(scores)[-5000:][::-1]
        # make it into a set
        sorted_indices = set(sorted_indices)
        # sort candidate by time
        candidate = sorted(sorted_indices)
        candidates.append(candidate)
        scores_selected.append([scores[i] for i in candidate])

    # Step 3: Build valid combinations with temporal constraints
    main_event = query.main_event
    times_selected = [[segments[i][0] for i in c] for c in candidates]

    valid_combos = sliding_window_combinations_with_main(
        times_selected,
        scores_selected,
        main_event=main_event,
        allow_none=True,
        window_size=window_size,
        stride=window_size // 20,
    )

    top_combos = valid_combos

    # Step 4: Rank combinations by total score
    top_n = min(len(valid_combos), 1000)
    weights = np.array([1.0] * len(queries))
    weights[main_event] = 1.5  # Give more weight to the main event
    total_scores = [
        sum(
            scores_selected[d][idx] * weights[d]
            for d, idx in enumerate(combo)
            if idx is not None
        )
        + 0.1 * sum(1 for idx in combo if idx is not None)  # small bonus per match
        for combo in valid_combos
    ]
    top_idxs = np.argsort(total_scores)[-top_n:][::-1]  # Get top N indices
    top_combos = [valid_combos[i] for i in top_idxs]

    # Step 5: Map back to segment and photo IDs
    top_segment_ids = [
        [
            candidates[d][combo[d]] if combo[d] is not None else None
            for d in range(len(queries))
        ]
        for combo in top_combos
    ]

    top_scores = np.array(total_scores)[top_idxs].tolist()

    merged_results, merged_scores = merge_results(
        segment_scores,
        top_segment_ids,
        top_scores,
        SIGLIP_FEATURES[data].ids,
        segments,
        allow_none=False,
        events=segmented_events,
    )

    # put events into before, main, after
    events: List[TripletEvent] = []
    for result in merged_results:
        if not result:
            continue
        main = segment_to_event(
            data,
            result[main_event],
        )
        if not main:
            continue

        before = None
        if main_event > 0:
            before = segment_to_event(
                data,
                [image for res in result[:main_event] for image in res],
            )

        after = None
        if main_event < len(result) - 1:
            after = segment_to_event(
                data,
                [image for res in result[main_event + 1 :] for image in res],
            )

        # check if there are no overlapping images
        if before and after:
            if (
                set(before.images) & set(after.images)
                or set(before.images) & set(main.images)
                or set(after.images) & set(main.images)
            ):
                continue

        events.append(
            TripletEvent(
                main=main,
                before=before,
                after=after,
            )
        )

    # Map segment scores to image scores (mainly for visualization)
    image_scores = np.zeros(len(SIGLIP_FEATURES[data].ids), dtype=float)
    for _, (segment, merged_score) in enumerate(zip(merged_results, merged_scores)):
        for image in segment[main_event]:
            idx = SIGLIP_FEATURES[data].image_to_id_map.get(image, -1)
            if idx >= 0:
                image_scores[idx] = max(merged_score, image_scores[idx])
    high_score_indices = np.where(image_scores > 0)[0].tolist()

    return SegmentResult(
        segments=[],
        segment_scores=merged_scores,
        scores=image_scores.tolist(),
        high_score_indices=high_score_indices,
        events=events,
    )


# # top_results = [
# #     [SIGLIP_FEATURES[data].ids[p]
# #      for seg_id in segment_group
# #      for p in range(*fixed_segments[seg_id])]
# #     for segment_group in top_segment_ids
# # ]

# events = []
# for segment_group in top_segment_ids:
#     event = Event(
#         start_time=fixed_segments[segment_group[0]][0],
#         end_time=fixed_segments[segment_group[-1]][-1],
#         images=[SIGLIP_FEATURES[data].ids[i] for i in segment_group],
#     )
#     events.append(event)

# return SegmentResult(
#     segment_scores=[total_scores[i] for i in top_idxs],
#     scores=[similarities[i] for i in top_idxs],
#     high_score_indices=top_idxs.tolist(),
#     events=events,
# )


@timer("get_segments_related_to_text")
async def get_segments_related_to_text(
    query: str,
    data: Data = Data.LSC23,
    filters: set[str] | None = None,
):
    photo_ids = SIGLIP_FEATURES[data].ids
    features = SIGLIP_FEATURES[data].embeddings
    model = get_model_by_name("siglip")

    similarities = await get_lsc25_scores(
        model, SingleQuery(full_text=query), include_only=filters, data=data
    )
    segment_scores = get_all_segment_scores_from_scores(similarities.tolist(), data)
    non_zeros = np.where(np.array(segment_scores) > 0)[0]
    non_zero_scores = np.array(segment_scores)[non_zeros]
    print(f"Found {len(non_zeros)} segments with non-zero scores")

    # rerank segments
    results = []
    scores = []
    hits = []
    score_threshold = np.percentile(non_zero_scores, 90)
    print(f"Score threshold: {score_threshold}")
    lower_score_threshold = np.percentile(non_zero_scores, 50)

    print("Reranking segments")
    segments, segment_photos, *_ = presegments[data]
    for i in range(len(segment_scores)):
        if segment_scores[i] <= 0:
            continue

        images = [photo for photo in segment_photos[i] if photo not in blurred[data]]
        start, end = segments[i]
        score = segment_scores[i]
        results += [(start, end)]
        okay = False
        if score > score_threshold:
            okay = True
        else:
            photo_scores = similarities[start:end]
            score = np.mean(photo_scores)
            if score > score_threshold:
                okay = True
            elif score > lower_score_threshold:
                # keyframes = get_keyframes_from_segments(encoded_query, data, images)
                # keyframes = [k.src if isinstance(k, Image) else k for k in keyframes]
                # score = reranker.score(
                #     data,
                #     query,
                #     keyframes,
                #     prompt="Is anyone eating or drinking in these images? Answer with True or False.",
                #     tokens=["True", "False"],
                # )
                # if score > 0.5:
                #     print("Reranked", score)
                #     okay = True
                # else:
                rerank = send_deakin_rerank_request(
                    images,
                    instruction="Is anyone eating or drinking?",
                )
                rerank["score"] = score
                print("Deakin rerank", rerank)
                if rerank["is_eating"]:
                    okay = True
                    score = score * 1.5
        if okay:
            scores.append(score)
            hits.append(True)
        else:
            scores.append(-1)
            hits.append(False)

    print(
        f"Filtered to {len([s for s in scores if s > -1])} segments"
    )
    assert len(results) == len(scores)

    # merge consecutive segments that have the same category
    threshold = THRESHOLD
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
    filtered_indices = set(range(len(photo_ids)))
    if filters is not None:
        filtered_indices = set(
            i for i, photo_id in enumerate(photo_ids) if photo_id in filters
        )

    heatmap = get_heatmap_from_images(
        images=[photo_ids[i] for i in filtered_indices],
        scores=[similarities[i] for i in filtered_indices],
    )

    return {
        "segments": results,
        "segment_scores": scores,
        "scores": similarities.tolist(),
        "heatmap": heatmap,
        "high_score_indices": [],
    }
