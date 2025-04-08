import base64
import os
import time
from collections.abc import AsyncGenerator
from io import BytesIO
from math import ceil
from typing import List

from configs import IMAGE_DIRECTORY
from llm import vllm_model
from llm.models import MixedContent
from llm.prompts import MIXED_PROMPTS
from PIL import Image as PILImage
from results.models import AnswerResult, Event, GenericEventResults, Image
from retrieval.async_utils import async_generator_timer
from rich import print as rprint


async def answer_visual_only(
    question: str,
    textual_descriptions: List[str],
    results: GenericEventResults,
    k: int = 10,
) -> AsyncGenerator[List[AnswerResult], None]:
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
        message = get_openai_visual_message(e.images)
        if message:
            content.append(message)
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
    task = vllm_model.generate_from_mixed_media(content)
    async for llm_response in task:
        try:
            rprint(llm_response)
            if llm_response and "answers" in llm_response:
                answers = llm_response["answers"]
                answer_list = []
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
                            )
                        )
                yield answer_list
        except Exception as e:
            rprint(e)
            rprint("GPT", llm_response)


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

def to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"


def get_openai_visual_message(image_paths: List[Image]) -> MixedContent | None:
    images = [os.path.join(IMAGE_DIRECTORY, img.src) for img in image_paths]
    image_objs = []
    for image in images:
        try:
            image_objs.append(PILImage.open(image))
        except Exception as e:
            print("Error opening image", image)
            continue
    if len(image_objs) == 0:
        return

    # join the images into a collage
    row = ceil(len(image_objs) ** 0.5)
    col = ceil(len(image_objs) / row)

    # create a collage of images
    min_size = (256, 256)

    # Resize images to fit in a uniform grid
    images = [img.resize(min_size) for img in image_objs]

    # Create the blank collage image
    collage_size = (min_size[0] * col, min_size[1] * row)
    collage = PILImage.new("RGB", collage_size)

    # Paste images into the collage
    for index, img in enumerate(images):
        x_offset = (index % col) * min_size[0]
        y_offset = (index // col) * min_size[1]
        collage.paste(img, (x_offset, y_offset))

    # save the collage to a jpeg file
    file = BytesIO()
    collage.save(file, "JPEG")

    bs64_code = base64.b64encode(file.getvalue()).decode("utf-8")
    bs64_images = f"data:image/jpeg;base64,{bs64_code}"

    return MixedContent(type="image_url", content=bs64_images)


@async_generator_timer("answer_visual_with_text")
async def answer_visual_with_text(
    question: str, image_paths: List[Image], textual_description: str
) -> AsyncGenerator[list[dict], None]:
    """
    Given a natural language question and a list of scenes, returns the top k answers
    Note that the EventResults have already filtered the relevant fields
    """
    mixed_message = get_openai_visual_message(image_paths)
    if not mixed_message:
        yield []
        return
    content = [mixed_message]
    content.append(
        MixedContent(
            type="text",
            content=MIXED_PROMPTS.format(
                question=question, extra_info=textual_description
            ),
        )
    )
    task = vllm_model.generate_from_mixed_media(content)
    async for llm_response in task:
        try:
            if llm_response and "answers" in llm_response:
                yield llm_response["answers"]
        except Exception as e:
            rprint(e)
            rprint("GPT", llm_response)
