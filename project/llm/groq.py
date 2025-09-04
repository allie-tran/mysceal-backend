import asyncio
from collections.abc import Sequence
import os
from typing import List

from groq import Groq
from openai.types.chat import ChatCompletionMessageParam
from llm.models import LLM

# Set up ChatGPT generation model
GROQ_AI = os.environ.get("GROQ_API", "")
MODEL_NAME = os.environ.get("GROQ_MODEL_NAME", "")

models = ["llama-3.1-70b-versatile", "mixtral-8x7b-32768", "llama-3.3-70b-versatile", "llama-3.3-70b-specdec"]

# llama3-70b-8192 ok - didn't answer
# llama-3.1-70b-versatile too slow
# mixtral-8x7b-32768 - normal

# MODEL_NAME = "mixtral-8x7b-32768"
MODEL_NAME = "llama-3.3-70b-versatile"

class GroqLLM(LLM):
    def __init__(self, name):
        self.client = Groq(api_key=GROQ_AI)
        self.model_name = name

    def generate(
        self, messages: List[ChatCompletionMessageParam], model: str | None = None
    ):
        """
        Generate completions from a list of messages
        """
        completion = self.client.chat.completions.create(
            model=self.model_name, messages=messages,  # type: ignore
            temperature=0.1,
        )
        return completion.choices[0].message.content

# Load the model
groq_llm_model = GroqLLM(MODEL_NAME)
small_groq_llm_model = GroqLLM("mistral-saba-24b")

