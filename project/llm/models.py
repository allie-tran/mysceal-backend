import base64
import traceback
import json
import logging
from math import ceil
import os
from collections.abc import Sequence
from io import BytesIO
from typing import Dict, List, Literal, Optional

from configs import DEBUG, IMAGE_DIRECTORY, JSON_END_FLAG, JSON_START_FLAG
from database.requests import get_llm_outputs, save_llm_outputs
from openai import AsyncOpenAI
from faces.main import draw_bounding_boxes
from results.models import Image
from PIL import Image as PILImage

from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from partialjson.json_parser import JSONParser
from pydantic import BaseModel
from pyrate_limiter import Duration, Limiter, Rate
from query_parse.types.requests import Data
from rich import print
from llm.prompts import (CASTLE_INSTRUCTIONS, DEAKIN_INSTRUCTIONS, LSC_INSTRUCTIONS)

logging.getLogger("pyrate_limiter").setLevel(logging.WARNING)

parser = JSONParser()
parser.on_extra_token = lambda *_, **__: None

rate = Rate(3, Duration.SECOND)
limiter = Limiter(rate)

# Set up ChatGPT generation model
OPENAI_API = os.environ.get("OPENAI_API", "")
# MODEL_NAME = os.environ.get("MODEL_NAME", "")
# MODEL_NAME = "gpt-4o-mini"  # Default to a specific model if not set
# MODEL_NAME = "gpt-4.1-nano-2025-04-14"
MODEL_NAME = "gpt-4.1-mini-2025-04-14"
# MODEL_NAME = "gpt-4o"
BEST_MODEL_NAME = "gpt-4o"
SEARCH_MODEL_NAME = "gpt-4o-mini-search-preview"


class MixedContent(BaseModel):
    type: Literal["text", "image_url"]
    content: str | bytes


class LLM:
    # Set up the template messages to use for the completion
    template_message: Dict[Data, ChatCompletionMessageParam] = {
        Data.LSC23: ChatCompletionSystemMessageParam(
            role="system", content=LSC_INSTRUCTIONS
        ),
        Data.Deakin: ChatCompletionSystemMessageParam(
            role="system", content=DEAKIN_INSTRUCTIONS
        ),
        Data.CASTLE: ChatCompletionSystemMessageParam(
            role="system", content=CASTLE_INSTRUCTIONS
        ),
    }

    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API)
        self.model_name = MODEL_NAME

    async def generate(
        self, messages: List[ChatCompletionMessageParam], advanced: bool = False
    ):
        """
        Generate completions from a list of messages
        """
        completion = await self.client.chat.completions.create(
            model=BEST_MODEL_NAME if advanced else self.model_name, messages=messages
        )

    def parse(self, response: str) -> Dict:
        # there might be MULTIPLE JSON objects in the response
        # we need to split them and parse them individually
        while JSON_START_FLAG in response:
            start = response.find(JSON_START_FLAG)
            response = response[start + len(JSON_START_FLAG) :]
            json_object = response
            if JSON_END_FLAG in response:
                end = response.find(JSON_END_FLAG)
                json_object = response[: end + len(JSON_END_FLAG)]
                response = response[end + len(JSON_END_FLAG) :]
            try:
                json_object = parser.parse(json_object)
                return json_object
            except json.JSONDecodeError or TypeError:
                traceback.print_exc()
                pass

        # if there is no JSON_START_FLAG, we return the response as is
        response = response.strip()
        if response:
            try:
                json_object = parser.parse(response)
                return json_object
            except json.JSONDecodeError:
                print("Error parsing object")
                print("[ERROR]", response)
        return {}

    def __generate_and_parse(
        self,
        messages: List[ChatCompletionMessageParam],
        stream=False,
        advanced: bool = False,
    ) -> Dict:
        """
        Generate completions from a list of messages
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        res = ""
        if DEBUG:
            print("Generating completions...")

        res = self.generate(messages, advanced=advanced)
        all_objects = {}
        if res is None:
            return {}

        assert isinstance(res, str), "Response should be a string"
        for obj in self.parse(res) or []:
            try:
                if obj:
                    all_objects.update(obj)
            except ValueError:
                print("Error parsing object")
                print("[ERROR]", obj)

        if not all_objects:
            print("[red]No JSON object found in the response.[/red]")
            print(res)

        return all_objects

    def generate_from_text(
        self, data: Data, text: str, 
        advanced: bool = False,
    ) -> Optional[Dict]:
        """
        Generate completions from text
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        model = BEST_MODEL_NAME if advanced else self.model_name
        cached_outputs = get_llm_outputs(prompt=text, model=model)
        if cached_outputs and cached_outputs.get("output"):
            if DEBUG:
                print("Using cached outputs")
            return cached_outputs["output"]

        messages = [self.template_message[data]]
        messages.append(ChatCompletionUserMessageParam(role="user", content=text))
        res = self.__generate_and_parse(messages, stream=False, advanced=advanced)
        # Store the output in the database
        save_llm_outputs(
            prompt=text,
            model=model,
            output=res,
        )
        return res

    def generate_from_mixed_media(
        self, data: Data, mixed_contents: Sequence[MixedContent],
        advanced: bool = False
    ):
        messages = [self.template_message[data]]
        content: List[ChatCompletionContentPartParam] = []
        for part in mixed_contents:
            if part.type == "text":
                content.append(
                    ChatCompletionContentPartTextParam(text=str(part.content), type="text")
                )
            elif part.type == "image_url":
                content.append(
                    ChatCompletionContentPartImageParam(
                        image_url=ImageURL(url=str(part.content)), type="image_url"
                    )
                )
        messages.append(ChatCompletionUserMessageParam(role="user", content=content))
        return self.__generate_and_parse(messages, advanced=advanced)


# Load the model and JSON parser
gpt_llm_model = LLM()

def to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        b64 = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"


def get_collage_image(data: Data, image_paths: List[str]):
    if data == Data.CASTLE:
        image_objs = draw_bounding_boxes(
            data, image_paths
        )
    else:
        image_objs = []
        for image in image_paths:
            try:
                image_objs.append(PILImage.open(image))
            except Exception:
                print("Error opening image", image)
                continue
        if len(image_objs) == 0:
            return

    # join the images into a collage
    row = ceil(len(image_objs) ** 0.5)
    if row == 0:
        print(f"No images to create a collage (length={len(image_objs)})")
        return None
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

    return collage



def get_openai_visual_message(image_paths: List[Image], data: Data = Data.LSC23) -> MixedContent | None:
    images = [os.path.join(IMAGE_DIRECTORY, data, img.src) for img in image_paths]
    collage = get_collage_image(data, images)
    if not collage:
        return None

    # save the collage to a jpeg file
    file = BytesIO()
    collage.save(file, "JPEG")

    bs64_code = base64.b64encode(file.getvalue()).decode("utf-8")
    bs64_images = f"data:image/jpeg;base64,{bs64_code}"

    return MixedContent(type="image_url", content=bs64_images)
