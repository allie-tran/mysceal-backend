"""
All utilities related to question answering
"""

import re
from typing import Dict, List, TypedDict

from configs import QUERY_PARSER
from llm import small_llm_model, llm_model
from llm.prompt.parse import PARSE_FILTERS, QUERY_PARSE_PROMPT, QUESTION_CLASSIFICATION, REWRITE_QUERY, REWRITE_QUESTION, SPLIT_QUERY_PROMPT
from rich import print as rprint

from query_parse.types.lifelog import SearchFilters, ParsedQuery, SingleQuery
from query_parse.types.requests import Data

from .constants import AUXILIARY_VERBS, QUESTION_WORDS, STOP_WORDS


def detect_question(query: str) -> bool:
    """
    Check if the query is a question or not
    This is useful in case the user forgets to toogle question mode
    """
    if "?" in query:
        return True

    # detect mutli-sentence questions
    sentences = re.split(r"[.!?,]", query)
    for sentence in sentences:
        words = sentence.lower().strip().split()
        if words:
            # check if the first word is a question word
            if words[0] in QUESTION_WORDS:
                return True

            if len(words) > 1:
                if words[0] in AUXILIARY_VERBS and words[1] in QUESTION_WORDS:
                    return True
    return False


async def question_to_retrieval(data: Data, text: str, is_question: bool) -> str:
    """
    Convert a question to a retrieval query
    """
    if not is_question:
        return text

    prompt = REWRITE_QUESTION.format(question=text)
    print("Converting question to retrieval query")
    search_text = small_llm_model.generate_from_text(data, prompt)
    if isinstance(search_text, dict) and "text" in search_text:
        search_text = search_text["text"]
    if search_text and isinstance(search_text, str):
        return search_text
    return text


def detect_simple_query(query: str) -> bool:
    """
    Check if the query is a simple query or not
    if it's too short, or full of stop words, it's a simple query
    """
    words = query.split()
    words = [word for word in words if word not in STOP_WORDS]
    return len(words) < 5


async def parse_query(
    data: Data,
    text: str, is_question: bool, search_filters: SearchFilters | None = None
) -> ParsedQuery:
    """
    Get the relevant fields from the query
    """

    text = text.strip()
    text = text.replace('‘', "'").replace('’', "'")  # replace fancy quotes with regular quotes

    # template = {
    # 	"main": defaultdict(lambda: search_text),
    # 	"after": defaultdict(str),
    # 	"hours_after": "1-2",
    # 	"before": defaultdict(str),
    # 	"hours_before": "1-2",
    # 	"must_not": defaultdict(str),
    # }

    # prompt = PARSE_NEGATION.format(query=text)
    # response = await gpt_llm_model.generate_from_text(prompt)
    # if isinstance(response, dict) and "text" in response:
    #     print(response)
    #     text = response["text"]
    #     main = SingleQuery(visual=text, location=text, time=text, date=text)
    #     must_not = response.get("must_not", "")
    #     if must_not:
    #         must_not = SingleQuery(visual=must_not, location=must_not, time=must_not, date=must_not)
    #         return ParsedQuery(main=main, must_not=must_not)
    #     else:
    #         return ParsedQuery(main=main)
    # main = SingleQuery(visual=text, location=text, time=text, date=text)
    # return ParsedQuery(main=main)

    if QUERY_PARSER or is_question or search_filters:
        # in some cases, it's inefficient to parse the query
        if search_filters is None and detect_simple_query(text):
            main = SingleQuery(visual=text, location=text, time=text, date=text)
            return ParsedQuery(queries=[main], main_event=0)

        res = await lsc25_get_parse_queries(data, text)
        events = res.get("events", [])
        filters = res.get("filters", {})
        parsed = ParsedQuery(queries=[], main_event=res.get("main_event", 0))
        if filters:
            print("Filters found in the response:", filters)
            if search_filters is None:
                search_filters = filters
            else:
                for key, value in filters.model_dump().items():
                    if hasattr(search_filters, key):
                        setattr(search_filters, key, value)
        for event in events:

            partial_query = SingleQuery(
                full_text=event.get("event", ""),
                visual=event.get("visual", ""),
                location=event.get("location", ""),
                time=event.get("time", ""),
                date="",
                filters=search_filters or SearchFilters(),
            )
            parsed.queries.append(partial_query)
        return parsed

    main = SingleQuery(visual=text, location=text, time=text, date=text, filters=search_filters or SearchFilters())
    return ParsedQuery(queries=[main], main_event=0)

class ParsedQueryResult(TypedDict):
    """
    Parsed query result type
    """
    queries: List[Dict[str, str]]
    main_event: int
    filters: SearchFilters

async def lsc25_get_parse_queries(data: Data, hint: str)-> ParsedQueryResult:
    parsed = llm_model.generate_from_text(data, QUERY_PARSE_PROMPT.format(query=hint))

    if parsed is None:
        rprint("[red]No results found for the query parsing. Using the hint as the event.[/red]")
        parsed = {"temporal_events": [hint], "max_time": 0, "main_event": 0}

    results = llm_model.generate_from_text(data, SPLIT_QUERY_PROMPT.format(
        summary=hint,
        events="\n".join(parsed.get("temporal_events", [])),
    ))

    print("Results from query splitting:", results)
    if not results:
        rprint("[red]No results found for the query splitting. Using the hint as the event.[/red]")
        results = {"events": [
            {
                "event": hint,
                "visual_information": hint,
                "temporal_information": "",
                "spatial_information": ""
            }
        ], "max_time": 0, "main_event": 0}
    results["max_time"] = parsed.get("max_time", 0)
    results["main_event"] = parsed.get("main_event", 0)


    if data == Data.CASTLE:
        search_filters = SearchFilters()
        res = llm_model.generate_from_text(
            data,
            PARSE_FILTERS.format(query=hint)
        )
        print("Results from filter parsing:", res)
        if isinstance(res, dict) and "filters" in res:
            filters = res["filters"]
            for key, value in filters.items():
                if hasattr(search_filters, key):
                    setattr(search_filters, key, value)

        results["filters"] = search_filters

    return results  # type: ignore


async def question_classification(data, question):
    FREQUENCY_QUESTION = ["how often", "how many times", "how frequently"]
    TIME_QUESTION = ["when", "what time", "how long", "how much time", "what date", "what month", "how long"]
    LOCATION_QUESTION = ["where", "what place", "what location", "what area", "what city", "what country", "which country", "which city", "which area", "name of the place", "name of the location", "name of the area", "name of the city", "name of the country"]

    question = question.lower()
    if any(word in question for word in FREQUENCY_QUESTION):
        return "frequency"
    if any(word in question for word in TIME_QUESTION):
        return "time"
    if any(word in question for word in LOCATION_QUESTION):
        return "location"

    prompt = QUESTION_CLASSIFICATION.format(question=question)
    response = small_llm_model.generate_from_text(data, prompt)
    if isinstance(response, dict) and "category" in response:
        return response["category"]
    else:
        rprint(response)
        return "visual"
