import asyncio
import heapq
import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, List, Optional

from configs import FILTER_FIELDS, MAX_IMAGES_PER_EVENT, MERGE_EVENTS
from database.main import image_collection
from database.models import GeneralRequestModel, Response
from database.requests import get_request
from database.utils import get_relevant_fields
from fastapi import HTTPException
from pydantic import BaseModel, PositiveInt, model_validator
from query_parse.es_utils import get_conditional_time_filters
from query_parse.extract_info import Query, create_es_query, create_query
from query_parse.question import detect_question, question_to_retrieval
from query_parse.types import ESSearchRequest
from query_parse.types.elasticsearch import ESBoolQuery, ESEmbedding, MSearchQuery
from query_parse.types.lifelog import TimeCondition
from query_parse.types.options import FunctionWithArgs, SearchPipeline
from query_parse.types.requests import (
    GeneralQueryRequest,
    MapRequest,
    TimelineDateRequest,
)
from query_parse.visual import encode_image
from question_answering.text import answer_text_only, get_specific_description
from results.models import (
    AnswerListResult,
    AnswerResult,
    AsyncioTaskResult,
    EventResults,
    GenericEventResults,
)
from results.utils import (
    RelevantFields,
    create_event_label,
    limit_images_per_event,
    merge_events,
)
from rich import print

from retrieval.search_utils import (
    get_search_function,
    merge_msearch_with_main_results,
    organize_by_relevant_fields,
    process_search_results,
    send_multiple_search_request,
    send_search_request,
)

logger = logging.getLogger(__name__)


async def streaming_manager(request: GeneralQueryRequest):
    """
    Managing the streaming of the search results
    """
    cached_responses = GeneralRequestModel(request=request)
    if cached_responses.finished:
        print("Cached responses found")
        # req = GeneralRequestModel.model_validate(cached_responses)
        # for response in req.responses:
        #     response.oid = req.oid
        #     data = response.model_dump_json()
        #     yield f"data: {data}\n\n"
        # print("[blue]ALl Done[/blue]")
        # print("-" * 50)
        # cached_responses.mark_finished()
        # yield "data: END\n\n"
        # return

    try:
        search_function = get_search_function(request, single_query, two_queries)
        async for response in search_function:
            cached_responses.add(response)
            data = response.model_dump_json()
            yield f"data: {data}\n\n"

    except asyncio.CancelledError:
        print("Client disconnected")

    except Exception as e:
        print("[red]Error[/red]", e)
        yield "data: ERROR\n\n"
        raise (e)

    print("[blue]ALl Done[/blue]")
    print("-" * 50)
    cached_responses.mark_finished()
    yield "data: END\n\n"


# ============================= #
# Easy Peasy Part: one query only
# ============================= #
async def simple_search(
    main_query: ESBoolQuery, size: int, tag: str = ""
) -> AsyncioTaskResult:
    """
    Search a single query without any fancy stuff
    """
    async_results = AsyncioTaskResult(results=None, tag=tag, task_type="search")

    print(f"[blue]Min score {main_query.min_score:.2f}[/blue]")
    search_request = ESSearchRequest(
        query=main_query.to_query(),
        sort_field="start_timestamp",
        min_score=main_query.min_score,
        size=size,
    )
    results = await send_search_request(search_request)

    if results is None:
        print("[red]No results found[/red]")
        return async_results

    async_results.results = results
    print(f"[green]Found {len(results)} events[/green]")
    results.min_score = main_query.min_score
    results.max_score = main_query.max_score

    # Give some label to the results
    results = create_event_label(results)

    # Just send the raw results first (unmerged, with full info)
    print("[green]Sending raw results...[/green]")
    return async_results


class Step(BaseModel):
    step: PositiveInt
    total: PositiveInt

    @model_validator(mode="after")
    def check_step(self):
        if self.step > self.total:
            raise ValueError("Step cannot be greater than total")
        return self

    def progress(self) -> int:
        return int((self.step / self.total) * 100)


async def single_query(
    text: str,
    pipeline: Optional[SearchPipeline] = None,
):
    """
    Search (and answer) a single query
    """

    if not pipeline:
        pipeline = SearchPipeline()

    step = Step(step=1, total=2)
    # ============================= #
    # 1. Query Parser (no skipping but modifiable)
    # ============================= #
    output = await pipeline.query_parser.async_execute(
        [
            FunctionWithArgs(
                function=detect_question, args=[text], output_name="is_question"
            ),
            FunctionWithArgs(
                function=question_to_retrieval,
                args=[text],
                use_previous_output=True,
                output_name="search_text",
                is_async=True,
            ),
            FunctionWithArgs(
                function=create_query,
                use_previous_output=True,
                output_name="query",
                is_async=True,
            ),
            FunctionWithArgs(  # no skipping
                function=create_es_query,
                use_previous_output=True,
                kwargs={"ignore_limit_score": False},
                output_name="es_query",
                is_async=True,
            ),
        ]
    )

    if output["is_question"]:
        step.total = 4
    pipeline.query_parser.add_output(output["query"].print_info())

    # ============================= #
    # 2. Search (Field extractor can be skipped)
    # ============================= #
    # a. Check if we need to extract the relevant fields
    field_extractor = pipeline.field_extractor
    to_extract_field = not field_extractor.executed and not field_extractor.skipped

    async_tasks = get_search_tasks(
        output["es_query"],
        pipeline.size,
        text,
        "single",
        to_extract_field,
    )

    # ----------------------------- #
    # b. Start the async tasks
    results = None
    relevant_fields = RelevantFields()

    for future in asyncio.as_completed(async_tasks):
        res = await future
        if res.task_type == "search":
            results = res.results
            step.step += 1
            yield Response(
                type="images",
                response=process_search_results(results),
                progress=step.progress(),
            )
        elif res.task_type == "llm":
            relevant_fields = res.results
            field_extractor.add_output(relevant_fields.model_dump())

    if results is None:
        print("[red]No results found[/red]")
        return

    # ============================= #
    # 3. Processing the results
    # ============================= #
    # a. Organize the results by relevant fields
    pipeline.field_organizer.default_output = {"results": results}
    print("Relevant fields", relevant_fields)
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
                args=[results, relevant_fields],
                output_name="results",
            )
        ]
    )["results"]

    # ----------------------------- #
    # c. Limit the images
    pipeline.image_limiter.default_output = {"results": results}
    results = pipeline.image_limiter.execute(
        [
            FunctionWithArgs(
                function=limit_images_per_event,
                args=[results, text, pipeline.image_limiter.output["max_images"]],
                output_name="results",
            )
        ]
    )["results"]

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
        results = create_event_label(results, relevant_fields.relevant_fields)

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
        return
    k = min(pipeline.top_k, len(results.events))

    print(f"[yellow]Answering the question for {k} events...[/yellow]")
    all_answers = AnswerListResult()
    async for answers in get_answer_tasks(
        text, results, relevant_fields.relevant_fields, k
    ):
        for answer in answers:
            all_answers.add_answer(answer)

        step.step += 1
        step.total += 1

        yield Response(
            progress=step.progress(), type="answers", response=all_answers.answers
        )

    if not all_answers:
        yield Response(progress=step.progress(), type="answers", response=[])


def get_search_tasks(
    main_query: ESBoolQuery,
    size: int,
    text: str,
    tag: str = "",
    filter_fields: bool = FILTER_FIELDS,
) -> List[asyncio.Task]:
    # Starting the async tasks
    async_tasks: Sequence = [asyncio.create_task(simple_search(main_query, size, tag))]
    if filter_fields and text:
        task = asyncio.create_task(get_relevant_fields(text, tag))
        async_tasks.append(task)
    return async_tasks


async def merge_generators(*generators: AsyncGenerator) -> AsyncGenerator[Any, None]:
    priority_queue = []
    next_idx = 0

    async def add_to_queue(generator, idx):
        nonlocal next_idx
        async for value in generator:
            heapq.heappush(priority_queue, (next_idx, value, idx))
            next_idx += 1

    tasks = [add_to_queue(generator, idx) for idx, generator in enumerate(generators)]
    await asyncio.gather(*tasks)

    while priority_queue:
        _, value, _ = heapq.heappop(priority_queue)
        yield value


async def get_answer_tasks(
    text: str,
    results: EventResults,
    relevant_fields: List[str],
    k: int = 10,
) -> AsyncGenerator[List[AnswerResult], None]:
    textual_descriptions = []
    for event in results.events[:k]:
        textual_descriptions.append(get_specific_description(event, relevant_fields))

    if not textual_descriptions:
        return

    print("[green]Textual description sample[/green]", textual_descriptions[0])
    k = min(k, len(results.events))
    async_tasks: Sequence = [
        answer_text_only(text, textual_descriptions, k),
        # answer_visual_with_text(text, textual_descriptions, results, k),
    ]
    async for task in merge_generators(*async_tasks):
        yield task


# ============================= #
# Level 2: Two queries
# ============================= #
async def add_conditional_filters_to_query(
    conditional_query: Query,
    main_results: EventResults,
    condition: TimeCondition,
) -> MSearchQuery:
    """
    Add the conditional filters to the query
    """
    es_query = await create_es_query(conditional_query)
    filters = get_conditional_time_filters(main_results, condition)

    msearch_queries = []
    for cond_filter in filters:
        clone_query = es_query.model_copy(deep=True)
        clone_query.filter.append(cond_filter)
        msearch_queries.append(clone_query)

    return MSearchQuery(queries=msearch_queries)


async def two_queries(
    main_text: str, conditional_text: str, condition: TimeCondition, size: int
):
    """
    Search for two related queries based on the time condition
    """
    is_question = detect_question(main_text)
    if is_question:
        search_text = await question_to_retrieval(main_text, is_question)
    else:
        search_text = main_text

    query = await create_query(search_text, is_question=is_question)
    es_query = await create_es_query(query, ignore_limit_score=False)
    conditional = await create_query(conditional_text, is_question=is_question)
    conditional_es_query = await create_es_query(conditional, ignore_limit_score=False)

    tasks = get_search_tasks(es_query, size, main_text, "main")
    tasks += get_search_tasks(
        conditional_es_query, size, conditional_text, "conditional"
    )

    # Starting the async tasks
    main_results, conditional_results, relevant_fields, conditional_relevant_fields = (
        None,
        None,
        None,
        None,
    )
    main_query, conditional_query = None, None

    for future in asyncio.as_completed(tasks):
        res: AsyncioTaskResult = await future
        task_type = res.task_type
        tag = res.tag

        if task_type == "search":
            assert isinstance(
                res.results, GenericEventResults
            ), "Results should be EventResults"
            if tag == "main":
                main_results = res.results
            elif tag == "conditional":
                conditional_results = res.results
        elif task_type == "llm":
            assert isinstance(res.results, list), "Results should be a list"
            if tag == "main":
                relevant_fields = res.results
            elif tag == "conditional":
                conditional_relevant_fields = res.results

    if (
        main_results is None
        or conditional_results is None
        or conditional_query is None
        or main_query is None
    ):
        print("[red]No results found[/red]")
        return

    # Add the conditional filters
    msearch_query = await add_conditional_filters_to_query(
        conditional_query, main_results, condition
    )

    # Send the search request
    print("[green]Sending the multi-search request...[/green]")
    msearch_results = await send_multiple_search_request(msearch_query)

    if not msearch_results:
        print("[red]No results found[/red]")
        return

    # Merge the two results
    merged_results = merge_msearch_with_main_results(
        main_results, msearch_results, condition
    )
    print("[green]Merged results[/green]", len(merged_results.events))
    yield {"type": "raw", "results": merged_results}

    # ============================= #
    # Processing...
    # ============================= #
    def apply_msearch(func: Callable, *args, **kwargs):
        return [func(res, *args, **kwargs) if res else None for res in msearch_results]

    changed = False
    if FILTER_FIELDS:
        if main_text and relevant_fields:
            main_results = organize_by_relevant_fields(main_results, relevant_fields)
        # if conditional_text and conditional_relevant_fields:
        #     conditional_results = organize_by_relevant_fields(
        #         conditional_results, conditional_relevant_fields
        #     )
        msearch_results = apply_msearch(
            organize_by_relevant_fields, conditional_relevant_fields
        )
        changed = True

    if MERGE_EVENTS:
        main_results = merge_events(main_results)  # TODO! add the relevant fields
        # conditional_results = merge_events(conditional_results)
        msearch_results = apply_msearch(merge_events)
        changed = True

    if MAX_IMAGES_PER_EVENT:
        print(f"[blue]Limiting images to {MAX_IMAGES_PER_EVENT}[/blue]")
        main_results = limit_images_per_event(
            main_results, main_text, MAX_IMAGES_PER_EVENT
        )
        # conditional_results = limit_images_per_event(
        #     conditional_results, conditional_text, MAX_IMAGES_PER_EVENT
        # )
        msearch_results = apply_msearch(
            limit_images_per_event, conditional_text, MAX_IMAGES_PER_EVENT
        )
        changed = True

    if changed:
        merged_results = merge_msearch_with_main_results(
            main_results, msearch_results, condition
        )
        # Give a different label:
        merged_results = create_event_label(merged_results)
        # Send the modified results
        yield {"type": "modified", "results": merged_results}

    # Answer the question
    if not is_question:
        return
    print("[yellow]Answering the question...[/yellow]")
    k = min(10, len(merged_results.events))
    textual_descriptions = []
    if main_results.relevant_fields or conditional_results.relevant_fields:
        for event in merged_results.events[:k]:
            main_description = get_specific_description(
                event.main, main_results.relevant_fields
            )
            conditional_description = get_specific_description(
                event.conditional, conditional_results.relevant_fields
            )
            textual_descriptions.append(
                f"{main_description}. About {condition.time_limit_str} {condition.condition} that, {conditional_description}"
            )
    if not textual_descriptions:
        return
    print("[green]Textual description sample[/green]", textual_descriptions[0])

    all_answers: AnswerListResult = AnswerListResult()

    async for new_answers in get_answer_tasks(
        main_text, main_results, main_results.relevant_fields, k
    ):
        for answer in new_answers:
            all_answers.add_answer(answer)
        yield {"type": "answers", "answers": all_answers}


def search_from_location(request: MapRequest) -> Optional[List[dict]]:
    """
    Search from the location
    """
    # Do another search with different location filter
    if request.es_id:
        raise NotImplementedError("Not implemented yet")

    # Just filter the results based on the location
    # Find main cached request with oid
    main_request = get_request(request.oid)
    if not main_request:
        print("[red]Main request not found[/red]")
        raise HTTPException(status_code=404, detail="I don't know how you got here")

    # Filter the results based on the location
    location = request.location
    results = main_request["responses"][0]["response"]

    assert results, "Results should not be empty"
    location = location.lower()
    new_results = []
    for event in results:
        loc = event["main"]["location"].lower()
        if location in loc:
            new_results.append(event["main"])

    if not new_results:
        print(f"[red]No results found for location {location}[/red]")
        return None

    return new_results


def search_from_time(request: TimelineDateRequest) -> Optional[List[dict]]:
    """
    Filter down the search from the timeline view
    """
    # Do another search with different time filter
    if request.es_id:
        raise NotImplementedError("Not implemented yet")

    # Just filter the results based on the time
    # Find main cached request with oid
    main_request = get_request(request.oid)
    if not main_request:
        print("[red]Main request not found[/red]")
        raise HTTPException(status_code=404, detail="I don't know how you got here")

    # Filter the results based on the time
    date = datetime.strptime(request.date, "%d-%m-%Y")
    start_time = date.replace(hour=0, minute=0, second=0)
    end_time = date.replace(hour=23, minute=59, second=59)
    results = main_request["responses"][0]["response"]
    all_scenes = []
    for event in results:
        # event is a triplet event now
        for k in ["before", "main", "after"]:
            if k in event:
                all_scenes.extend(event[k]["images"])

    filtered = image_collection.find(
        {
            "start_timestamp": {"$gte": start_time, "$lte": end_time},
            "image": {"$in": all_scenes},
        }
    )
    return list(filtered)


async def search_similar_events(image: str) -> Optional[EventResults]:
    """
    Search for similar events
    """
    image_feat = encode_image(image)
    if not image_feat:
        return None

    # Find the similar events
    es = ESBoolQuery()
    es.must.append(ESEmbedding(embedding=image_feat.tolist()))

    result = await simple_search(es, size=200, tag="similar")
    assert isinstance(
        result.results, GenericEventResults
    ), "Results should be EventResults"

    if not result.results.events:
        print("[red]No similar events found[/red]")
        return None

    return result.results
