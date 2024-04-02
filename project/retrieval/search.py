import asyncio
from collections.abc import Sequence
import logging
from typing import Literal, Optional, Tuple

from configs import DERIVABLE_FIELDS, FILTER_FIELDS, MAX_IMAGES_PER_EVENT, MERGE_EVENTS
from database.utils import convert_to_events, get_relevant_fields
from query_parse.extract_info import Query
from query_parse.question import detect_question, question_to_retrieval
from query_parse.types import ESSearchRequest
from question_answering.answer import answer_text_only
from results.models import EventResults
from results.utils import (
    create_event_label,
    deriving_fields,
    limit_images_per_event,
    merge_events,
)
from rich import print

from retrieval.search_utils import send_search_request

logger = logging.getLogger(__name__)

# ============================= #
# Easy Peasy Part: one query only
# ============================= #


async def simple_search(
    text_query: str, isQuestion: bool
) -> Tuple[Optional[EventResults], Literal["search"]]:
    """
    Search a single query
    without any fancy stuff
    """
    query = Query(text_query, is_question=isQuestion)
    main_query = await query.to_elasticsearch(ignore_limit_score=True)

    print("[blue]Min score[/blue]", main_query.min_score)
    search_request = ESSearchRequest(
        original_text=query.original_text,
        query=main_query.to_query(),
        sort_field="start_timestamp",
        min_score=main_query.min_score,
    )
    results = await send_search_request(search_request)

    if results is None:
        return None, "search"

    print(f"[green]Found {len(results)} events[/green]")
    results.min_score = main_query.min_score
    results.max_score = main_query.max_score

    # Give some label to the results
    results = create_event_label(results)

    # Just send the raw results first (unmerged, with full info)
    print("[green]Sending raw results...[/green]")
    return results, "search"


async def single_query(
    text: str,
):
    """
    Search (and answer) a single query
    """
    is_question = detect_question(text)
    if is_question:
        search_text = question_to_retrieval(text)
    else:
        search_text = text

    # Starting the async tasks
    async_tasks: Sequence = [asyncio.create_task(simple_search(search_text, is_question))]

    if FILTER_FIELDS and text:
        task = asyncio.create_task(get_relevant_fields(text))
        async_tasks.append(task)

    # Return the results when any of the tasks are done
    results = None
    relevant_fields = None
    for future in asyncio.as_completed(async_tasks):
        async_res, task_type = await future
        if task_type == "search":
            results = async_res
            yield {"type": "raw", "results": results}
        elif task_type == "llm":
            relevant_fields = async_res

    if results is None:
        print("[red]No results found[/red]")
        return

    changed = False
    # Get the relevant fields
    if FILTER_FIELDS and text and relevant_fields:
        scene_ids = [event.scene for event in results.events]
        results.relevant_fields = relevant_fields
        results.events = convert_to_events(scene_ids, relevant_fields)
        derivable_fields = set(relevant_fields) & set(DERIVABLE_FIELDS)
        if derivable_fields:
            print(f"[green]Deriving {derivable_fields} [/green]")
            new_events = deriving_fields(results.events, list(derivable_fields))
            results.events = new_events
        changed = True

    # Merge the results
    if MERGE_EVENTS:
        results = merge_events(results)
        changed = True

    if MAX_IMAGES_PER_EVENT:
        results = limit_images_per_event(results, text, MAX_IMAGES_PER_EVENT)
        changed = True

    if changed:
        # Give a different label:
        results = create_event_label(results)
        print(f"[green]Processed into {len(results)} events[/green]")
        # Send the modified results
        yield {"type": "modified", "results": results}

    if not is_question:
        return

    # Answer the question
    print("[yellow]Answering the question...[/yellow]")
    answers = await answer_text_only(text, results)
    print("[green]Answers:[/green]", answers)
    if answers in ["N/A", "VQA"]:
        # No answers found from text
        # Try with images
        print("[orange]No answers found from text. Trying with images...[/orange]")
        answers = []
    yield {"type": "answers", "answers": answers}


# ============================= #
# Level 2: Multiple queries
# ============================= #

# pass for now TODO!
