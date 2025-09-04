import asyncio
import pandas as pd
import logging
import time
import requests
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple


from configs import FILTER_FIELDS, WINDOW_SIZE
from database.main import get_db, group_collection, image_collection, scene_collection
from database.models import GeneralRequestModel, Response
from database.requests import get_es, get_parsed_output, get_request
from database.utils import get_relevant_fields, segments_to_events
from fastapi import HTTPException
from pydantic import InstanceOf
from pympler import asizeof
from query_parse.extract_info import Query, modify_es_query
from query_parse.question import detect_question, parse_query
from query_parse.types.elasticsearch import TimeInfo
from query_parse.types.lifelog import DateTuple, Mode, ParsedQuery, SearchFilters
from query_parse.types.options import FunctionWithArgs, SearchPipeline
from query_parse.types.requests import (
    AnswerThisRequest,
    Data,
    EditSearch,
    GeneralQueryRequest,
    MapRequest,
    Step,
    Task,
    TimelineDateRequest,
)
from question_answering import filter_answers, get_answer_tasks
from question_answering.text import get_specific_description
from question_answering.video import answer_visual_with_text
from results.models import (
    AnswerListResult,
    AnswerResultWithEvent,
    AsyncioTaskResult,
    DerivedEvent,
    Event,
    EventResults,
    HeatmapResults,
    Image,
    PartialEvent,
    TimelineGroup,
    TimelineResult,
    TimelineScene,
    TripletEvent,
    TripletEventResults,
)
from results.utils import (
    RelevantFields,
    create_event_label,
    limit_images_per_event,
    merge_events,
)
from rich import print
from visual import encode_text
from visual.features import SIGLIP_FEATURES
from visual.main import get_model
from visual.segments import get_keyframes_from_segments

from retrieval.async_utils import async_generator_timer, async_timer
from retrieval.graph_utils import get_heatmap_data
from retrieval.lsc25 import (
    get_segments_from_similarity_scores,
    get_segments_related_to_text,
    lsc25_get_segments,
    lsc25_multi_queries,
)
from retrieval.search_utils import (
    get_raw_search_results,
    get_search_request,
    organize_by_relevant_fields,
    process_search_results,
)

logger = logging.getLogger(__name__)


def get_human_readable_size(obj: Any) -> str:
    """
    Get the human readable size
    """
    size = asizeof.asizeof(obj)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


@async_generator_timer("streaming_manager", track_yield=True)
async def streaming_manager(request: GeneralQueryRequest) -> AsyncGenerator[str, None]:
    """
    Managing the streaming of the search results
    """
    try:
        cached_responses = GeneralRequestModel(request=request)
        if cached_responses.finished:
            print("Cached responses found")
            req = GeneralRequestModel.model_validate(cached_responses)
            for response in req.responses:
                if response.type in ["images", "modified"]:
                    res = [
                        TripletEvent.model_validate(event)
                        for event in response.response
                    ]
                    response.response = res
                if response.type == "heatmap":
                    res = [
                        HeatmapResults.model_validate(heatmap)
                        for heatmap in response.response
                    ]
                    response.response = res
                response.oid = req.oid
                data = response.model_dump_json(by_alias=True)
                yield f"data: {data}\n\n"
        else:
            search_function = perform_full_search(request)
            async for response in search_function:
                # Save the response
                response.oid = cached_responses.oid
                cached_responses.add(response)

                print("[red]" + "-" * 50 + "[/red]")
                print(f"[red]Yielding response[/red]", response.type)
                print(f"[red]Size of the response[/red]", len(response.response))
                print("[red]" + "-" * 50 + "[/red]")
                now = time.time()
                data = response.model_dump_json(by_alias=True)
                yield f"data: {data}\n\n"
                print("[red]Time taken to yield[/red]", time.time() - now)

        print("[blue]ALl Done[/blue]")
        yield "data: END\n\n"
        print("-" * 50)
        cached_responses.mark_finished()

    except asyncio.CancelledError as e:
        print("[red]Cancelled[/red]", e)
        yield "data: CANCELLED\n\n"

    # client disconnected
    except GeneratorExit as e:
        print("[red]Generator Exit[/red]", e)
        yield "data: CANCELLED\n\n"

    except Exception as e:
        print("[red]Error[/red]", e)
        yield "data: ERROR\n\n"
        raise (e)


# ============================= #
# Easy Peasy Part: one query only
# ============================= #
@async_timer("simple_search")
async def simple_search(
    query: ParsedQuery,
    search_filters: SearchFilters,
    data: Data,
    size: int,
    tag: str = "",
    mode: Mode = Mode.event,
    edit_search: Optional[EditSearch] = None,
) -> AsyncioTaskResult[TripletEventResults]:
    """
    Search a single query without any fancy stuff
    """
    results = None
    if query.multiple_queries and data == Data.LSC23:
        print("[green]Multiple queries found[/green]")
        segment_res = await lsc25_multi_queries(
            query,
            data,
            window_size=edit_search.window_size if edit_search else WINDOW_SIZE,
        )

    else:
        segment_res = await lsc25_get_segments(
            data,
            query.main,
            search_filters,
            top_n=size,
            score_percentile=99 if data == Data.LSC23 else 90,
        )

    events = segment_res.events

    print("[green]Events found[/green]", len(events))
    results = TripletEventResults(
        events=events, scores=segment_res.segment_scores[:size]
    )

    # The scores are on a x-axis of time
    # We can visualize the scores in a heatmap like git commit history
    # of the scores
    if data == Data.LSC23:
        visualisation_data = get_heatmap_data(
            data, segment_res.scores, segment_res.high_score_indices
        )
    else:
        visualisation_data = []
    # filter_fields = main_query.filters
    # if filter_fields and filter_fields.patient_id:
    #     visualisation_data.extend(
    #         get_deakin_heatmap_per_hours(
    #             data,
    #             segment_res.scores,
    #             segment_res.high_score_indices,
    #             filter_fields.patient_id,
    #         )
    #     )

    # Give some label to the results
    if results:
        print(f"[green]Found {len(results.events)} matches for {mode}[/green]")
        results = create_event_label(data, results)
        results.heatmap = visualisation_data
    return AsyncioTaskResult(task_type="search", tag=tag, results=results)


async def get_segments_only(
    main_text: str, filters: SearchFilters, data: Data
) -> Tuple[List[Event], int, List[bool], HeatmapResults | None]:
    """
    Get the segments only
    """
    db = get_db(data)
    mongo_query = {
        "patient.id": {"$in": filters.patient_id},
    }
    if [x for x in filters.date if x]:
        mongo_query["date"] = {"$in": filters.date}
    print("[green]Mongo Query[/green]", mongo_query)
    images_cursor = (
        image_collection(db).find(mongo_query, {"image": 1}).sort("image", 1)
    )  # Project only the required field
    images = [doc["image"] for doc in images_cursor]
    first_image = images[0] if images else None
    last_image = images[-1] if images else None
    if not first_image or not last_image:
        print("[red]No images found in the database[/red]")
        return [], 0, [], None

    images = set(images)
    first_index = SIGLIP_FEATURES[data].ids.index(first_image)
    last_index = SIGLIP_FEATURES[data].ids.index(last_image)

    if len(images) == 0:
        print("[red]No images found[/red]")
        return [], 0, [], None

    print("[green]Images found[/green]", len(images))
    # segment_res = get_segments(main_text, data, max_gap=5, filters=images, to_merge=True)
    segment_res = await get_segments_related_to_text(main_text, data, filters=images)
    eating = []

    if not segment_res["segments"]:
        print("[red]No segments found[/red]")
        # return the full list of images
        all_segments = [(first_index, last_index)]
        all_scores = [-1]
        eating = [False]
    else:
        eating = []
        print("[green]Total segments found[/green]", len(segment_res["segments"]))
        # Ignore the score and just sort by time
        ids = sorted(
            range(len(segment_res["segments"])),
            key=lambda x: segment_res["segments"][x][0],
        )
        # Add in the segments inbetween
        all_segments = []
        all_scores = []
        i = 0
        while i < len(ids):
            start, end = segment_res["segments"][ids[i]]
            if first_index < start:
                eating.append(False)
                all_segments.append((first_index, start))
                all_scores.append(-1)
            all_segments.append((start, end))
            all_scores.append(segment_res["segment_scores"][ids[i]])
            eating.append(True)
            i += 1
            first_index = end

        if first_index < last_index:
            all_segments.append((first_index, last_index))
            all_scores.append(-1)
            eating.append(False)

        print(
            "[green]Both eating and non-eating segments found[/green]",
            len(all_segments),
        )

    events = segments_to_events(
        data,
        all_segments,
        all_scores,
        SIGLIP_FEATURES[data].ids,
    )
    print("[green]Events found[/green]", len(events))
    return events, len(images), eating, segment_res["heatmap"]



@async_generator_timer("single_query")
async def perform_full_search(
    request: GeneralQueryRequest,
):
    """
    Search (and answer) a single query
    """
    now = time.time()
    text: str = request.main
    filters: SearchFilters = request.filters or SearchFilters()
    data: Data = request.data or Data.LSC23
    print("[green]Data[/green]", data)
    pipeline: Optional[SearchPipeline] = request.pipeline
    task_type: Task = request.task_type or Task.NONE
    edit_search = request.edit_search

    if not pipeline:
        pipeline = SearchPipeline()

    step = Step(step=1, total=2)
    # ============================= #
    # 1. Query Parser (no skipping but modifiable)
    # ============================= #
    if pipeline.query_parser.executed:
        output = pipeline.query_parser.output
    else:
        parsed = get_parsed_output(text, data)
        output = None
        if parsed:
            for response in parsed["responses"]:
                if response["type"] == "pipeline":
                    response = response["response"]
                    parsed_pipeline = SearchPipeline.model_validate(response)
                    parsed_output = parsed_pipeline.query_parser.output
                    output = {
                        "query": ParsedQuery.model_validate(parsed_output),
                        "is_question": parsed_output["isQuestion"],
                    }
                    print("[green]Using cached query parser output[/green]")
                    break
        if not output:
            output = await pipeline.query_parser.async_execute(
                [
                    FunctionWithArgs(
                        function=detect_question, args=[text], output_name="is_question"
                    ),
                    FunctionWithArgs(
                        function=parse_query,
                        kwargs={"data": data, "text": text, "search_filters": filters},
                        use_previous_output=True,
                        output_name="query",  # ParsedQuery
                        is_async=True,
                    ),
                ]
            )

    print("--> Query Parser", time.time() - now)
    if output["is_question"]:
        step.total = 4

    configs = output["query"].model_dump()
    pipeline.query_parser.add_output(configs)
    pipeline.multiple_queries = output["query"].multiple_queries
    pipeline.window_size = edit_search.window_size if edit_search else WINDOW_SIZE

    # ============================= #
    # 2. Search (Field extractor can be skipped)
    # ============================= #
    # a. Check if we need to extract the relevant fields
    field_extractor = pipeline.field_extractor
    skip_extract = task_type == Task.AD_HOC
    async_tasks = get_search_tasks(
        output["query"],
        filters,
        pipeline.size,
        text,
        data,
        tag="multiple" if output["query"].multiple_queries else "single",
        filter_fields=not skip_extract,
        edit_search=edit_search,
    )

    # ----------------------------- #
    # b. Start the async tasks
    results = None
    relevant_fields = RelevantFields()

    now = time.time()
    for future in asyncio.as_completed(async_tasks):
        res = await future
        if res.task_type == "search":
            results = res.results
            step.step += 1
            yield Response(
                type="images",
                response=process_search_results(results),
                progress=step.progress(),
                # es_id=output["query"].oid,
            )
            if results and results.heatmap:
                yield Response(
                    type="heatmap",
                    response=results.heatmap,
                    progress=step.progress(),
                )
            print("--> Search", time.time() - now)
        elif res.task_type == "llm":
            relevant_fields = res.results
            field_extractor.add_output(relevant_fields.model_dump())
            print("--> Field Extractor", time.time() - now)

    if results is None:
        print("[red]single_query: No results found[/red]")
        return

    now = time.time()
    # ============================= #
    # 3. Processing the results
    # ============================= #
    # a. Organize the results by relevant fields
    pipeline.field_organizer.default_output = {"results": results}
    results = pipeline.field_organizer.execute(
        [
            FunctionWithArgs(
                function=organize_by_relevant_fields,
                args=[results, relevant_fields.relevant_fields],
                output_name="results",
            )
        ]
    )["results"]

    # ----------------------------- #
    # b. Merge the events
    pipeline.event_merger.default_output = {"results": results}
    results = pipeline.event_merger.execute(
        [
            FunctionWithArgs(
                function=merge_events,
                args=[
                    f"query: {text}",
                    data,
                    results,
                    relevant_fields,
                ],
                output_name="results",
            )
        ]
    )["results"]

    # ----------------------------- #
    # c. Limit the images
    pipeline.image_limiter.default_output = {"results": results}
    if task_type != Task.AD_HOC:
        results = pipeline.image_limiter.execute(
            [
                FunctionWithArgs(
                    function=limit_images_per_event,
                    args=[
                        results,
                        text,
                        pipeline.image_limiter.output["max_images"],
                        data,
                    ],
                    output_name="results",
                )
            ]
        )["results"]

    print("--> Processing", time.time() - now)

    # ----------------------------- #
    # d. Check if anything changed
    # Not actually part of the pipeline
    unchanged = all(
        p.skipped
        for p in [
            pipeline.field_organizer,
            pipeline.event_merger,
            pipeline.image_limiter,
        ]
    )
    if not unchanged:
        print("[blue]Some changes detected[/blue]")
        # get keyframes from segments
        encoded_query = encode_text(text)
        for event in results.events:
            if not event.main.keyframes:
                event.main.keyframes = get_keyframes_from_segments(
                    encoded_query, data, event.main.images
                )

        results = create_event_label(data, results, relevant_fields.relevant_fields)

    step.step += 1
    yield Response(
        progress=step.progress(),
        type="modified",
        response=process_search_results(results),
    )
    yield Response(
        progress=step.progress(), type="pipeline", response=pipeline.export()
    )

    # ============================= #
    # 4. Answer the question
    # ============================= #
    if not output["is_question"]:
        print("[yellow]Not a question. Skipping the answer[/yellow]")
        return

    print("[yellow]Answering the question...[/yellow]")
    all_answers = AnswerListResult()
    answers = await get_answer_tasks(
        data, text, results, relevant_fields.relevant_fields
    )

    for answer in answers:
        all_answers.add_answer(answer)

    step.step += 1
    step.total += 1

    # ======================= #
    # Test
    if len(all_answers) > 1:
        final_answers = await filter_answers(data, text, all_answers)
        if final_answers:
            all_answers = final_answers

    if all_answers:
        yield Response(
            progress=step.progress(), type="answers", response=all_answers.export()
        )
    else:
        yield Response(progress=step.progress(), type="answers", response=[])


def get_search_tasks(
    query: ParsedQuery,
    search_filters: SearchFilters,
    size: int,
    text: str,
    data: Data,
    tag: str = "",
    filter_fields: bool = FILTER_FIELDS,
    edit_search: Optional[EditSearch] = None,
) -> List[asyncio.Task]:
    tasks = []

    tasks.append(
        simple_search(
            query,
            search_filters,
            data,
            size,
            tag,
            mode=Mode.event,
            edit_search=edit_search,
        )
    )
    if filter_fields and text:
        tasks.append(get_relevant_fields(data, text, tag))

    # Starting the async tasks
    async_tasks = [asyncio.create_task(task) for task in tasks]
    return async_tasks




@async_timer("search_from_location")
async def search_from_location(
    request: MapRequest,
) -> Optional[List[InstanceOf[Event]]]:
    """
    Search from the location
    """
    # Do another search with different location filter
    if request.es_id:
        print("[green]Searching from location again...[/green]")
        # return await search_location_again(request)

    # Just filter the results based on the location
    # Find main cached request with oid
    main_request = get_request(request.oid)
    if not main_request:
        print(f"[red]Main request not found for oid {request.oid}[/red]")
        raise HTTPException(status_code=404, detail="I don't know how you got here")

    # Filter the results based on the location
    location = request.location
    results = main_request["responses"][0]["response"]

    assert results, "Results should not be empty"
    assert location, "Location should not be empty"

    location = location.lower()

    new_results = []
    for event in results:
        loc = event["main"]["location"].lower()
        if location in loc:
            new_results.append(event["main"])

    if not new_results:
        print(f"[red]No results found for location {location}[/red]")
        return None

    return [PartialEvent(**event) for event in new_results]


@async_timer("search_from_time")
async def search_from_time(request: TimelineDateRequest) -> TimelineResult:
    """
    Filter down the search from the timeline view
    """
    db = get_db(request.data)
    all_images = []

    # Filter the results based on the time
    date = datetime.strptime(request.date, "%d-%m-%Y")
    start_time = date.replace(hour=0, minute=0, second=0)

    # Do another search with different time filter
    all_images = await try_search_again(request, date)
    print("[green]Found images[/green]", len(all_images))

    # Just filter the results based on the time
    filtered = image_collection(db).find({"image": {"$in": all_images}}).sort("time", 1)
    filtered = list(filtered)
    all_groups = set([image["group"] for image in filtered])

    # Find time info
    group_docs = (
        group_collection(db)
        .find(
            {
                "group": {"$in": list(all_groups)},
            }
        )
        .sort("time", 1)
    )

    group_info = {group["group"]: group for group in group_docs}

    # Group by group -> scene -> images
    groups: Dict[str, List[TimelineScene]] = defaultdict(list)
    for image_dict in filtered:
        image: Image = Image(src=image_dict["image"], **image_dict)
        scene: str = image_dict["scene"]
        group: str = image_dict["group"]

        key = f"{scene}-{image.src}"
        groups[group].append(TimelineScene(images=[image], scene=key))

    timeline_groups: List[TimelineGroup] = []
    for group in groups:
        scenes = groups[group]
        timeline_groups.append(
            TimelineGroup(
                group=group,
                location=group_info[group]["location"],
                location_info=group_info[group]["location_info"],
                time_info=[group_info[group]["time_info"]],
                scenes=scenes,
            )
        )
    print("[green]Found groups[/green]", len(timeline_groups))
    return TimelineResult(result=timeline_groups, date=start_time)


@async_timer("try_search_again")
async def try_search_again(request, date) -> List[str]:
    if not request.es_id:
        return []

    # Do another search with different time filter
    query_doc = get_es(request.es_id)
    if not query_doc:
        print("[red]Query not found[/red]")
        return []

    query_doc["oid"] = query_doc.pop("_id")
    query = Query.model_validate(query_doc)
    time_info = TimeInfo(
        dates=[DateTuple(year=date.year, month=date.month, day=date.day)]
    )
    new_query = await modify_es_query(query, time=time_info, mode=Mode.image)
    if new_query:
        search_request = get_search_request(new_query, size=20, mode=Mode.image)
        print(search_request.min_score)
        results = await get_raw_search_results(search_request)
        all_images = results.results or []
        return all_images

    return []


@async_timer("search_similar_events")
async def search_similar_events(image: str, data: Data) -> Optional[EventResults]:
    """
    Search for similar events
    """
    model = get_model(data)
    similarity = model.find_similar_images(image, data)
    print("[green]Similarity scores found[/green]", similarity.shape)

    segment_result = get_segments_from_similarity_scores(similarity, data=data)

    result = TripletEventResults(
        events=segment_result.events,
        scores=segment_result.segment_scores,
    )

    if not result.events:
        print("[red]No similar events found[/red]")
        return None

    print("[green]Found similar events[/green]", len(result.events))
    # create labels for the events
    result = create_event_label(data, result)

    # result.heatmap = get_heatmap_data(
    #     data, segment_result.scores, segment_result.high_score_indices
    # )

    return result


@async_generator_timer("answer_single_event")
async def answer_single_event(
    request: AnswerThisRequest,
    data: Data = Data.LSC23,
) -> AsyncGenerator[AnswerResultWithEvent, None]:
    """
    Answer the question for a single event
    """
    db = get_db(data)

    # Get scene information from the image
    scene = scene_collection(db).find_one(
        {"images": {"$elemMatch": {"src": request.image}}}
    )

    if not scene:
        print("[red]Scene not found[/red]")
        raise HTTPException(status_code=404, detail="Scene not found")

    event = DerivedEvent(**scene)
    textual_description = get_specific_description(data, event, request.relevant_fields)

    images = [Image(**x) for x in scene["images"]]

    async for answers in answer_visual_with_text(
        data, request.question, images, textual_description
    ):
        if answers:
            for answer_dict in answers:
                answer = answer_dict["answer"]
                explanation = answer_dict["explanation"]
                yield AnswerResultWithEvent(
                    text=answer, explanation=[explanation], evidence=[event]
                )
