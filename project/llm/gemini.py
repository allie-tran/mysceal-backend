import os
from collections.abc import Sequence
from typing import Dict, List

from configs import IMAGE_DIRECTORY
from dotenv import load_dotenv
from google import genai  # type: ignore
from google.genai.types import Content, GenerateContentConfig, Part  # type: ignore
from partialjson.json_parser import JSONParser
from pyrate_limiter import Duration, Limiter, Rate
from query_parse.types.requests import Data
from results.models import Image
from rich import print

from llm.prompts import CASTLE_INSTRUCTIONS, DEAKIN_INSTRUCTIONS, LSC_INSTRUCTIONS

from .models import LLM, MixedContent

load_dotenv()

DEBUG = True
JSON_START_FLAG = "```json"
JSON_END_FLAG = "```"

parser = JSONParser()
parser.on_extra_token = lambda *_, **__: None

rate = Rate(3, Duration.SECOND)
limiter = Limiter(rate)

# Set up ChatGPT generation model
GEMINI = os.environ.get("GEMINI_API", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "")
BEST_MODEL_NAME = "gemini-2.5-flash"


class Gemini(LLM):
    # Set up the template messages to use for the completion
    system_instruction: Dict[Data, str] = {
        Data.LSC23: LSC_INSTRUCTIONS,
        Data.Deakin: DEAKIN_INSTRUCTIONS,
        Data.CASTLE: CASTLE_INSTRUCTIONS,
    }

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI)
        self.model_name = MODEL_NAME

    def generate_gemini(self, data: Data, contents: Content, advanced: bool = False):
        """
        Generate completions from a list of messages
        """
        request = self.client.models.generate_content(
            model=BEST_MODEL_NAME if advanced else self.model_name,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=self.system_instruction[data]
            ),
        )
        response = request.text
        if not response:
            print("[red]No response from Gemini[/red]")
            return {}
        if DEBUG:
            print(f"[blue]Gemini response: {response}[/blue]")
        return self.parse(response)

    def generate_from_text(self, data: Data, text: str, advanced: bool = False):
        """
        Generate completions from text
        Then parse the JSON object from the completion
        If the completion is not a JSON object, return the text
        """
        contents = Content(role="user", parts=[Part.from_text(text=text)])
        return self.generate_gemini(data, contents, advanced)

    def generate_from_mixed_media(
        self, data: Data, mixed_contents: Sequence[MixedContent],
        advanced: bool = False
    ):
        parts: List[Part] = []
        for part in mixed_contents:
            if part.type == "text":
                parts.append(Part.from_text(text=str(part.content)))
            elif part.type == "image_url":
                parts.append(Part.from_bytes(data=part.content, mime_type="image/jpeg"))  # type: ignore
        return self.generate_gemini(data, Content(role="user", parts=parts), advanced)


def get_visual_content(
    images: List[Image], data: Data = Data.LSC23
) -> List[MixedContent]:
    """
    Get a visual message for OpenAI from a list of image paths.
    """
    if not images:
        return []

    image_paths = [os.path.join(IMAGE_DIRECTORY, data, img.src) for img in images]
    messages = []
    for image_path in image_paths:
        try:
            image_bytes = open(image_path, "rb").read()
            messages.append(MixedContent(type="image_url", content=image_bytes))
        except OSError as e:
            print(f"Error reading image {image_path}: {e}")
            continue
    return messages

gemini = Gemini()
