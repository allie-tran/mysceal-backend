from typing import List, Optional, Set

import numpy as np
from configs import WINDOW_SIZE
from database.utils import segment_to_event, segments_to_events
from pydantic import BaseModel
from query_parse.types.lifelog import ParsedQuery, SingleQuery
from query_parse.types.requests import Data
from results.models import TripletEvent
from rich import print
from visual.features import SIGLIP_FEATURES
from visual.low_visual import blurred
from visual.main import ClipModel, get_model
from visual.segments import get_segments_from_top_photos, merge_results, presegments
from visual.types import Array1D

from retrieval.async_utils import async_timer, timer


class SegmentResult(BaseModel):
    segment_scores: List[float]
    scores: List[float]
    high_score_indices: List[int]
    events: List[TripletEvent]


@async_timer("lsc25_get_segments")
async def lsc25_get_segments(
    query: SingleQuery,
    data: Data = Data.LSC23,
    score_percentile: int = 99,
    include_only: Optional[Set[str]] = None,
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

    _, fixed_segments, photo_to_segment_id, _ = presegments[data]

    segments, segment_scores = get_segments_from_top_photos(
        top_photos,
        top_similarities.tolist(),
        fixed_segments,
        photo_to_segment_id,
        blurred[data],
    )

    all_images = []
    for photos in segments:
        all_images.extend(photos)

    events = segments_to_events(
        data,
        segments,
        segment_scores,
        SIGLIP_FEATURES[data].ids,
    )
    return SegmentResult(
        segment_scores=segment_scores,
        scores=similarities.tolist(),
        high_score_indices=high_score_indices,
        events=[TripletEvent(main=event) for event in events],
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

    for t0 in range(min_time, max_time, stride):
        t1 = t0 + window_size
        combo = []
        matched_main = False

        for q in range(num_queries):
            query_times = times_selected[q]
            query_scores = scores_selected[q]

            matches = [
                (i, t, query_scores[i])
                for i, t in enumerate(query_times)
                if t0 < t < t1
            ]

            if matches:
                best_idx, _, _ = max(matches, key=lambda x: x[2])
                combo.append(best_idx)
                if q == main_event:
                    matched_main = True

            else:
                combo.append(None)

        if not allow_none:
            if None in combo:
                continue

        def is_increasing(i,j, t1, t2):
            if t1 is None or t2 is None:
                return True
            return times_selected[i][t1] < times_selected[j][t2]

        if matched_main:
            valid = all(
                is_increasing(i, i + 1, combo[i], combo[i + 1])
                for i in range(num_queries - 1)
            )
            if valid:
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
        await get_lsc25_scores(model, query, include_only, data, visual_only=main_event != i) for i, query in enumerate(queries)
    ]

    segment_scores = [
        get_all_segment_scores_from_scores(similarities[i].tolist(), data)
        for i in range(N)
    ]

    # Step 2: Select top candidates based on percentiles, max 2000
    candidates = [] # list of list of segment indices
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
        times_selected, scores_selected, main_event=main_event, allow_none=True,
        window_size=window_size, stride=window_size // 20
    )

    top_combos = valid_combos

    # Step 4: Rank combinations by total score
    top_n = min(len(valid_combos), 1000)
    weights = np.array([1.0] * len(queries))
    weights[main_event] = 1.5  # Give more weight to the main event
    total_scores = [
        sum(scores_selected[d][idx] * weights[d] for d, idx in enumerate(combo) if idx is not None)
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
        events=segmented_events
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
