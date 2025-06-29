import json
import logging
from collections.abc import AsyncGenerator
from copy import deepcopy
from typing import Any, Callable, List, Optional, Sequence, Union

import requests
from configs import DERIVABLE_FIELDS, ES_URL
from database.utils import convert_to_events
from elastic_transport import ObjectApiResponse
from fastapi import HTTPException
from query_parse.types.elasticsearch import ESBoolQuery, ESSearchRequest, MSearchQuery
from query_parse.types.lifelog import Mode, TimeCondition
from query_parse.types.requests import Data, GeneralQueryRequest, Task
from requests import Response
from results.models import (
    AsyncioTaskResult,
    DoubletEvent,
    DoubletEventResults,
    EventResults,
    GenericEventResults,
    TripletEvent,
    TripletEventResults,
)
from results.utils import create_event_label, deriving_fields
from rich import print

from retrieval.types import ESResponse

logger = logging.getLogger(__name__)

json_headers = {"Content-Type": "application/json"}


def clean(data: Any) -> dict:
    """
    Print the data in a clean format
    If any array is found, print only the first 5 elements
    """
    data = deepcopy(data)
    if not isinstance(data, dict):
        return data  # type: ignore
    for key, value in data.items():
        if isinstance(value, list):
            data[key] = [clean(d) for d in value[:5]]
        elif isinstance(value, dict):
            data[key] = clean(value)
    return data


# ======================== #
# MAIN REQUEST FUNCTIONS
# ======================== #
async def send_explain_request(query: ESSearchRequest, doc_id: str):
    """
    Send an explain request
    """
    json_query = query.to_query()["query"]
    json_query = {"query": json_query}

    # encode "/" in the doc_id
    doc_id = doc_id.replace("/", "%2F")

    # Use normal search
    response = requests.post(
        f"{ES_URL}/{query.index}/_explain/{doc_id}",
        data=json.dumps(json_query),
        headers=json_headers,
    )
    if response.status_code != 200:
        handle_failed_request(response, json_query)
        raise HTTPException(
            status_code=500, detail="Error with the Elasticsearch request"
        )
    print(response.json())


async def send_search_request(query: ESSearchRequest) -> ESResponse:
    """
    Send a new search request
    """
    json_query = query.to_query()
    # Use normal search
    response = requests.post(
        f"{ES_URL}/{query.index}/_search{'?scroll=5m' if query.scroll else ''}",
        data=json.dumps(json_query),
        headers=json_headers,
    )
    if response.status_code != 200:
        handle_failed_request(response, json_query)
        raise HTTPException(
            status_code=500, detail="Error with the Elasticsearch request"
        )
    if "bool" in json_query["query"]:
        print(clean(json_query))
        # await send_explain_request(query, response.json()["hits"]["hits"][0]["_id"])
        # if "clip_vector" in response.json()["hits"]["hits"][0]["_source"]:
        #     text_vector = None
        #     query_vector = json_query["query"]["bool"]["should"]
        #     if isinstance(query_vector, list):
        #         for q in query_vector:
        #             if "elastiknn" in q:
        #                 query_vector = q
        #     else:
        #         text_vector = query_vector["elastiknn_nearest_neighbors"]["vec"]["values"]
        #     if text_vector:
        #         image_vector = response.json()["hits"]["hits"][0]["_source"]["clip_vector"]
        #         similarity = np.dot(text_vector, image_vector)
        #         similarity = similarity / (np.linalg.norm(text_vector) * np.linalg.norm(image_vector))
        #         print(f"Similarity: {similarity:.2f}")
    return ESResponse.model_validate(response.json())


async def send_multiple_search_request(
    data: Data,
    queries: MSearchQuery,
) -> Sequence[Optional[EventResults]]:

    response = requests.get(
        f"{ES_URL}/_msearch",
        data=queries.to_query(),
        headers={"Content-Type": "application/x-ndjson"},
    )

    if response.status_code != 200:
        handle_failed_request(response, queries.to_query())
        return []

    response_json = response.json()  # Convert to json as dict formatted
    list_events: List[Optional[EventResults]] = []
    for res in response_json["responses"]:
        try:
            event_ids = [d["_source"]["scene"] for d in res["hits"]["hits"]]
            if len(event_ids) == 0:
                list_events.append(None)
                continue
            events = EventResults(
                events=convert_to_events(event_ids),
                scores=[d["_score"] for d in res["hits"]["hits"]],
            )
            events = create_event_label(data, events)
            list_events.append(events)
        except KeyError:
            print("KeyError", res)
            list_events.append(None)

    return list_events


def handle_failed_request(
    response: Union[Response, ObjectApiResponse], query: Any
) -> None:
    logger.error(f"There was an error with the request: ({response.status_code})")
    logger.error(response.text)
    with open("request.log", "a") as f:
        f.write(response.text + "\n")
        f.write(json.dumps(query) + "\n")


def delete_scroll_id(scroll_id) -> None:
    response = requests.delete(
        f"{ES_URL}/_search/scroll",
        data=json.dumps({"scroll_id": scroll_id}),
        headers=json_headers,
    )
    if response.status_code != 200:
        handle_failed_request(response, {"scroll_id": scroll_id})


# ======================================== #
# PRE-PROCESSING FUNCTIONS
# ======================================== #
def get_search_request(
    main_query: ESBoolQuery,
    size: int,
    mode: Mode = Mode.event,
) -> ESSearchRequest:
    """
    Get the search request
    """
    print(f"[blue]Min score {main_query.min_score:.2f}[/blue]")
    search_request = ESSearchRequest(
        query=main_query.to_query(),
        min_score=main_query.min_score,
        size=size,
        mode=mode,
        sort_field="start_timestamp" if mode == Mode.event else "timestamp",
        sort_order="asc",
        mongo_match=main_query.to_mongo(),
    )
    return search_request


async def get_raw_search_results(
    request: ESSearchRequest, tag: str = ""
) -> AsyncioTaskResult[List[str]]:
    """
    Get the raw search results
    """
    response = await send_search_request(request)
    if not response:
        return AsyncioTaskResult(results=None, tag=tag, task_type="search")

    return AsyncioTaskResult(
        results=[d.source[request.main_field] for d in response.hits.hits],
        tag=tag,
        task_type="search",
    )


async def get_search_results(
    data: Data, request: ESSearchRequest
) -> EventResults | None:
    es_response = await send_search_request(request)
    results = process_es_results(es_response, request.test, request.mode)

    if results is None:
        print("[red]get_search_results: No results found[/red]")
        return None

    print(f"[green]Found {len(results)} events[/green]")
    # Give some label to the results
    results = create_event_label(data, results)

    # Just send the raw results first (unmerged, with full info)
    return results


# ======================================== #
# POST-PROCESSING FUNCTIONS
# ======================================== #
def process_es_results(
    response: ESResponse,
    test: bool = False,
    mode: Mode = Mode.event,
) -> EventResults | None:
    important_field = "scene" if mode == "event" else "image_path"
    ids = [doc.source[important_field] for doc in response.hits.hits]
    if len(ids) == 0:
        print("[red]process_es_results: No results found![/red]")
    scores = [doc.score for doc in response.hits.hits]

    # Get the relevant fields and form the EventResults object
    if test and response.aggregations:
        if isinstance(scores[0], float):
            max_score = scores[0]
        else:
            max_score = 1.0
        min_score = 0.0
        aggs = response.aggregations
        min_score = aggs["score_stats"]["std_deviation_bounds"]["upper"]
        # It is a test query, so we don't need to return the events
        return EventResults(
            events=[],
            scores=[],
            min_score=min_score,
            max_score=max_score,
        )

    # ------------------------- #
    # Organize the results
    # ------------------------- #
    key = "scene" if mode == "event" else "image"
    events = convert_to_events(ids, key=key)

    result = EventResults(events=events, scores=scores)
    return result


def merge_msearch_with_main_results(
    main_results: EventResults,
    msearch_results: Sequence[EventResults | None],
    time_condition: TimeCondition,
    merge_msearch: bool = False,
) -> DoubletEventResults:
    """
    Merge the msearch results with the main results
    Strategy:
    - For each event in the main results, get the first event in the msearch results
    - Create a doublet event with the main event as the main and the msearch event as the conditional
    - Sort the doublets by the score

    If merge_msearch is True, then any main event that has the same msearch event will be merged
    Strategy:
    - Keep track of the msearch events that have been used using a dictionary
    - For each event in the main results, get the first event in the msearch results
    - If the msearch event has been used, then find the event that has the same msearch event
    - Create a doublet event with the main event as the main and the msearch event as the conditional
    """
    events = main_results.events
    scores = main_results.scores

    doublets: list[DoubletEvent] = []
    doublet_scores: list[float] = []
    used_msearch = {}

    assert len(events) == len(msearch_results)

    for i, msearch_result in enumerate(msearch_results):
        if (
            msearch_result is None
            or not msearch_result.events
            or not msearch_result.events[0].images
        ):
            continue

        if merge_msearch:
            scene = msearch_result.events[0].scene
            # Check if the msearch event has been used
            if scene in used_msearch:
                # Find the event that has the same msearch event
                j = used_msearch[scene]
                doublets[j].main.merge_with_one(
                    events[i], [doublet_scores[j], scores[i]]
                )
                continue
            used_msearch[scene] = i

        doublets.append(
            DoubletEvent(
                main=events[i],
                conditional=msearch_result.events[0],
                condition=time_condition,
            )
        )
        doublet_scores.append(scores[i] + msearch_result.scores[0])

    # Sort the doublets by the score
    sorted_indices = sorted(range(len(doublet_scores)), key=lambda k: doublet_scores[k], reverse=True)
    doublets = [doublets[i] for i in sorted_indices]
    doublet_scores = [doublet_scores[i] for i in sorted_indices]

    return DoubletEventResults(events=doublets, scores=doublet_scores)


def organize_by_relevant_fields(results: TripletEventResults, relevant_fields) -> TripletEventResults:
    print(f"[green]Organizing by relevant fields: {relevant_fields}[/green]")
    images = [image.src for event in results.events for image in event.main.images]
    main_events = convert_to_events(images, relevant_fields, key="image")
    # Create a new TripletEventResults with the main events
    for event, main_event in zip(results.events, main_events):
        event.main = main_event
    results.relevant_fields = relevant_fields

    derivable_fields = set(relevant_fields) & set(DERIVABLE_FIELDS)
    if derivable_fields:
        events = [event.main for event in results.events]
        new_events = deriving_fields(events, list(derivable_fields))
        for event, new_event in zip(results.events, new_events):
            event.main = new_event

    return results


def process_search_results(results: GenericEventResults) -> List[TripletEvent]:
    # This is the search results
    if not results:
        return []
    assert not isinstance(results, str)

    # Format into EventTriplets
    triplet_results = []
    for main in results.events:
        if isinstance(main, TripletEvent):
            # If it's already a triplet, just add it
            triplet_results.append(main)
            continue
        triplet = TripletEvent(main=main)
        if isinstance(main, DoubletEvent):
            if main.condition.condition == "before":
                triplet.before = main.conditional
            else:
                triplet.after = main.conditional

        triplet_results.append(triplet)
    # Yield the results
    return triplet_results
