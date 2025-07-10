import os
from typing import List

import torch
from configs import FORCE_CPU, IMAGE_DIRECTORY
from query_parse.types.requests import Data
from question_answering.video import get_collage_image
from results.models import Event
from tqdm.auto import tqdm
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration


processor_path = "Qwen/Qwen2-VL-2B-Instruct"
model = "lightonai/MonoQwen2-VL-v0.1"
# model = "mistralai/Mistral-Small-3.1-24B-Instruct-2503"
# model = "mistralai/Pixtral-12B-2409"
# model = "mistralai/Ministral-8B-Instruct-2410"

# model_path = "Tarsier2-7b-0115"
device = "cpu"
if not FORCE_CPU and torch.cuda.is_available():
    device = "cuda"


class Reranker:
    def __init__(self, processor_path, model_path):
        self.processor = AutoProcessor.from_pretrained(processor_path)
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_path,
            attn_implementation="flash_attention_2",
            torch_dtype=torch.bfloat16,
            device_map=device,
        )

    def score(self, data: Data, query: str, image_paths: list[str], prompt: str = "",
              tokens=["True", "False"]
              ):
        image_paths = [
            os.path.join(IMAGE_DIRECTORY, data, image_path)
            for image_path in image_paths
        ]
        collage = get_collage_image(image_paths)
        if not collage:
            return 0.0
        if not prompt:
            prompt = (
                "Assert the relevance of the previous image document to the following query/question, "
                "answer True or False. The query is: {query}"
            ).format(query=query)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": collage},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        # Apply chat template and tokenize
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(text=text, images=[collage], return_tensors="pt").to(
            device
        )

        # Run inference to obtain logits
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_for_last_token = outputs.logits[:, -1, :]
            output_logits = outputs.logits

        decoded_text = self.processor.batch_decode(
            output_logits.argmax(dim=-1), skip_special_tokens=True
        )[0]
        print(f"Decoded text: {decoded_text}")
        # Convert tokens and calculate relevance score
        true_token_id = self.processor.tokenizer.convert_tokens_to_ids(tokens[0])
        false_token_id = self.processor.tokenizer.convert_tokens_to_ids(tokens[1])
        relevance_score = torch.softmax(
            logits_for_last_token[:, [true_token_id, false_token_id]], dim=-1
        )

        # Extract and display probabilities
        true_prob = relevance_score[0, 0].item()
        return true_prob

    def rerank(self, data: Data, query: str, image_paths: list[str]):
        print(f"Reranking {len(image_paths)} images")
        scores = [
            self.score(data, query, [image_path]) for image_path in tqdm(image_paths)
        ]
        return scores

    def rerank_scenes(self, data: Data, query: str, scenes: List[Event]):
        scores: List[float] = []
        print(f"Reranking {len(scenes)} scenes")
        for scene in tqdm(scenes):
            score = self.score(data, query, [image.src for image in scene.keyframes])
            scores.append(score)
        return scores


# reranker = None
# reranker = Reranker(processor_path, model)
# print("Reranker initialized")
