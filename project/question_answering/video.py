from collections.abc import AsyncGenerator
from typing import List

from llm import get_visual_content, vllm_model
from llm.models import MixedContent
from llm.prompts import MIXED_PROMPTS
from query_parse.types.requests import Data
from results.models import AnswerResult, Event, GenericEventResults, Image
from retrieval.async_utils import async_generator_timer
from rich import print as rprint


def answer_visual_only(
    data: Data,
    question: str,
    textual_descriptions: List[str],
    results: GenericEventResults,
    k: int = 10,
) -> List[AnswerResult]:
    """
    Answer the question using the visual information only
    K: number of events to consider
    """
    # if internlm_model.loaded:
    #     internlm_model.load_model()

    # Get the list of images
    content = [
        MixedContent(
            type="text",
            content="""Answering questions based on the images and their metadata.
Give one or more of your best guess to the question in the following format, with each answer being the key. The explantion should be brief. You don't have to give a full sentence, just list the reasons. The evidence should be the index of the event that supports the answer.

Give an empty list if you can't guess any answer.

Use the following schema in a valid JSON format:
Answers: List[Answer]
Answer:
- answer: str
- explanation: str
- evidence: List[int]

```json
{{
    "answers": [
        {{
            "answer": "something",
            "explanation": "brief explanation for why the answer is `something`",
            "evidence": [1, 2, 3]
        }},
        {{
            "answer": "one",
            "explanation": "brief explanation for why the answer is `one`",
            "evidence": [4, 5]
        }},
        {{
            "answer": "5 days",
            "explanation": "brief explanation for why the answer is `5 days`",
            "evidence": [6]
        }}
    ]
}}
```
""",
        )
    ]
    for i, (event, description) in enumerate(
        zip(results.events[:k], textual_descriptions[:k])
    ):
        e = event if isinstance(event, Event) else event.main
        message = get_visual_content(e.images[:20], data=data)
        if message:
            content.extend(message)
            content.append(
                MixedContent(
                    type="text",
                    content=f"{i + 1}. {description}",
                )
            )
        # async for answers in answer_visual_one_event(i, question, description, e):
        #     yield answers

    content.append(
        MixedContent(
            type="text",
            content=f"\nThe question is: {question}",
        )
    )

    print(
        f"[green]Answering question with visual content only (k={k}, len(content)={len(content)})[/green]"
    )
    llm_response = vllm_model.generate_from_mixed_media(data, content, advanced=True)
    rprint(f"[green]LLM response received[/green]", llm_response)
    answer_list = []
    if llm_response and "answers" in llm_response:
        answers = llm_response["answers"]
        for answer_dict in answers:
            answer: str = answer_dict["answer"]
            explanation: str = answer_dict["explanation"]
            evidence: List[int] = answer_dict["evidence"]
            if not is_black_listed(answer):
                answer_list.append(
                    AnswerResult(
                        text=answer,
                        explanation=[explanation],
                        evidence=evidence,
                        source="visual",
                    )
                )
    return answer_list


black_list = [
    "I'm sorry",
    "I'm not sure",
    "I don't know",
    "I can't answer",
    "AI language model",
    "I cannot",
    "I can't",
    "I am sorry",
    "I am not sure",
    "I am not able",
    "The image does not",
    "The image is not",
    "The image is blurry",
    "The image is unclear",
    "The image doesn't",
    "There are no",
    "The image you provided",
    "The image is too",
    "blurry",
    "low-quality",
    "blurred",
]


def is_black_listed(answer: str) -> bool:
    """
    Check if the answer is in the black list
    """
    if not answer:
        return True
    for black in black_list:
        if black in answer:
            return True
    return False


@async_generator_timer("answer_visual_with_text")
async def answer_visual_with_text(
    data: Data, question: str, image_paths: List[Image], textual_description: str
) -> AsyncGenerator[list[dict], None]:
    """
    Given a natural language question and a list of scenes, returns the top k answers
    Note that the EventResults have already filtered the relevant fields
    """
    mixed_message = get_visual_content(image_paths, data=data)
    if not mixed_message:
        yield []
        return
    content = mixed_message
    content.append(
        MixedContent(
            type="text",
            content=MIXED_PROMPTS.format(
                question=question, extra_info=textual_description
            ),
        )
    )
    task = vllm_model.generate_from_mixed_media(data, content)
    if task:
        for llm_response in task:
            try:
                if llm_response and "answers" in llm_response:
                    yield llm_response["answers"]
            except Exception as e:
                rprint(e)
                rprint("GPT", llm_response)
