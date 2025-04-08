"""
All utilities related to question answering
"""

import re
from collections import defaultdict

from configs import QUERY_PARSER
from llm import small_llm_model
from llm.prompt.parse import PARSE_NEGATION, PARSE_QUERY, QUESTION_CLASSIFICATION, REWRITE_QUERY, REWRITE_QUESTION
from rich import print as rprint

from query_parse.types.lifelog import EatingFilters, ParsedQuery, SingleQuery

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


async def question_to_retrieval(text: str, is_question: bool) -> str:
    """
    Convert a question to a retrieval query
    """
    if not is_question:
        return text

    prompt = REWRITE_QUESTION.format(question=text)
    print("Converting question to retrieval query")
    search_text = await small_llm_model.generate_from_text(prompt)
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
    text: str, is_question: bool, eating_filters: EatingFilters | None = None
) -> ParsedQuery:
    """
    Get the relevant fields from the query
    """
    template = {
        "main": defaultdict(lambda: text),
        "after": defaultdict(str),
        "before": defaultdict(str),
        "must_not": defaultdict(str),
    }

    prompt = PARSE_NEGATION.format(query=text)
    response = await small_llm_model.generate_from_text(prompt)
    if isinstance(response, dict) and "text" in response:
        print(response)
        text = response["text"]
        main = SingleQuery(visual=text, location=text, time=text, date=text)
        must_not = response.get("must_not", "")
        if must_not:
            must_not = SingleQuery(visual=must_not, location=must_not, time=must_not, date=must_not)
            return ParsedQuery(main=main, must_not=must_not)
        else:
            return ParsedQuery(main=main)
    main = SingleQuery(visual=text, location=text, time=text, date=text)
    return ParsedQuery(main=main)

    if QUERY_PARSER or is_question or eating_filters:
        pass
        # # in some cases, it's inefficient to parse the query
        # if eating_filters is None and detect_simple_query(text):
        #     main = SingleQuery(visual=text, location=text, time=text, date=text)
        #     return ParsedQuery(main=main)

        # eating_query = eating_filters.format() if eating_filters else ""
        # if eating_query:
        #     eating_query = f"Eating filters: {eating_query}"

        # prompt = REWRITE_QUERY.format(query=text, eating_filters=eating_query)
        # search_text = await llm_model.generate_from_text(prompt)
        # if isinstance(search_text, dict) and "text" in search_text:
        #     print(search_text)
        #     text = search_text["text"]

        # prompt = PARSE_QUERY.format(
        #     query=text, eating_filters=eating_query
        # )
        # feat = await llm_model.generate_from_text(prompt)
        # if isinstance(feat, dict):
        #     for key, value in feat.items():
        #         if key in template:
        #             query = template[key]
        #             for k, v in value.items():
        #                 query[k] = v

        #             # add location into main
        #             if "location" in query and "visual" in query:
        #                 if query["location"] != query["visual"]:
        #                     query["visual"] = query["visual"] + " " + query["location"]

        # else:
        #     print("Failed to parse query")
        #     print(feat)

    parsed_query = ParsedQuery.model_validate(template)
    return parsed_query


async def question_classification(question):
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
    response = await small_llm_model.generate_from_text(prompt)
    if isinstance(response, dict) and "category" in response:
        return response["category"]
    else:
        rprint(response)
        return "visual"





