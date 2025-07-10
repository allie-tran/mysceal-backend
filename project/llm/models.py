import asyncio
import json
import os
from collections.abc import Sequence
from typing import AsyncGenerator, Dict, Generator, List, Literal, Optional

from configs import DEBUG, JSON_END_FLAG, JSON_START_FLAG
from openai import AsyncOpenAI, BaseModel
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
from pyrate_limiter import BucketFullException, Duration, Limiter, Rate
from database.requests import get_llm_outputs, save_llm_outputs
from retrieval.async_utils import async_generator_timer
from rich import print

from llm.prompts import INSTRUCTIONS
import logging
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
SEARCH_MODEL_NAME = "gpt-4o-mini-search-preview"


class MixedContent(BaseModel):
    type: Literal["text", "image_url"]
    content: str


class LLM:
    # Set up the template messages to use for the completion
    template_message: ChatCompletionMessageParam = ChatCompletionSystemMessageParam(
        role="system", content=INSTRUCTIONS
    )

    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API)
        self.model_name = MODEL_NAME

    async def generate(self, messages: List[ChatCompletionMessageParam], model: str | None = None):  # type: ignore
        """
        Generate completions from a list of messages
        """
        request = await self.client.chat.completions.create(
            model=model or self.model_name, messages=messages, stream=True
        )

        async for chunk in request:
            await asyncio.sleep(0)
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def __parse(self, response: str) -> Generator[Dict, None, None]:
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
                yield json_object
            except json.JSONDecodeError:
                pass
        # if there is no JSON_START_FLAG, we return the response as is
        response = response.strip()
        if response:
            try:
                json_object = parser.parse(response)
                yield json_object
            except json.JSONDecodeError:
                print("Error parsing object")
                print("[ERROR]", response)
                pass

    async def __generate_and_parse(
        self,
        messages: List[ChatCompletionMessageParam],
        stream=False,
        model: str | None = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate completions from a list of messages
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        res = ""
        if DEBUG:
            print("Generating completions...")

        async for completion in self.generate(messages, model=model):
            res += completion
            response = res
            await asyncio.sleep(0)

            if DEBUG:
                print(completion, end="")

            if stream:
                try:
                    limiter.try_acquire("1")
                    all_objects = {}
                    for obj in self.__parse(response):
                        try:
                            all_objects.update(obj)
                        except ValueError:
                            pass
                            print("Error parsing object")
                            print("[ERROR]", obj)
                    yield all_objects
                except BucketFullException:
                    continue

        all_objects = {}
        for obj in self.__parse(res):
            try:
                if obj:
                    all_objects.update(obj)
            except ValueError:
                print("Error parsing object")
                print("[ERROR]", obj)
                pass

        if not all_objects:
            print("[red]No JSON object found in the response.[/red]")
            print(res)

        yield all_objects

    async def generate_from_text(
        self, text: str, model: str | None = None
    ) -> Optional[Dict]:
        """
        Generate completions from text
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        cached_outputs = get_llm_outputs(
            prompt=text, model=model or self.model_name
        )
        if cached_outputs and cached_outputs.get("output"):
            if DEBUG:
                print("Using cached outputs")
            return cached_outputs["output"]

        messages = [self.template_message]
        messages.append(ChatCompletionUserMessageParam(role="user", content=text))
        res = None
        async for data in self.__generate_and_parse(messages, stream=False, model=model):
            await asyncio.sleep(0)
            res = data

        # Store the output in the database
        save_llm_outputs(
            prompt=text,
            model=model or self.model_name,
            output=res,
        )
        return res

    async def stream_from_text(
        self, text: str, model: str | None = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate completions from text
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        messages = [self.template_message]
        messages.append(ChatCompletionUserMessageParam(role="user", content=text))
        async for data in self.__generate_and_parse(messages, stream=True, model=model):
            yield data

    @async_generator_timer("generate_from_mixed_media")
    async def generate_from_mixed_media(
        self, data: Sequence[MixedContent]
    ) -> AsyncGenerator[Dict, None]:
        messages = [self.template_message]
        content: List[ChatCompletionContentPartParam] = []
        for part in data:
            if part.type == "text":
                content.append(
                    ChatCompletionContentPartTextParam(text=part.content, type="text")
                )
            elif part.type == "image_url":
                content.append(
                    ChatCompletionContentPartImageParam(
                        image_url=ImageURL(url=part.content), type="image_url"
                    )
                )
        messages.append(ChatCompletionUserMessageParam(role="user", content=content))
        async for completion in self.__generate_and_parse(messages):
            # if DEBUG:
            print("GPT", completion)
            yield completion


# Load the model and JSON parser
gpt_llm_model = LLM()
