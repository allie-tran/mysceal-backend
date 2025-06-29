import os
import pickle
from typing import List, Tuple

import numpy as np
import open_clip
import torch
from configs import CLIP_EMBEDDINGS, IMAGE_DIRECTORY, MODEL_NAME, PRETRAINED_DATASET
from numpy import linalg as LA
from open_clip.model import CLIP
from open_clip.tokenizer import _tokenizer
from PIL import Image as PILImage
from query_parse.types.lifelog import SingleQuery
from query_parse.types.requests import Data
from retrieval.async_utils import async_timer, timer
from rich import print
from transformers.models.auto.modeling_auto import AutoModel
from transformers.models.auto.processing_auto import AutoProcessor

from visual.features import SIGLIP_FEATURES, VIT14_CLIP_FEATURES
from visual.querybank_norm import apply_qb_norm_to_query, get_retrieved_videos
from visual.temporal_feat_extract import (
    get_time_heatmap,
    get_time_info,
    map_matrix_to_photos,
)
from visual.types import Array1D

# MODEL_NAME = "ViT-L-14-336"
# PRETRAINED_DATASET = "openai"
# DATA_DIRECTORY = "/home/allie/data_mysceal/"
# IMAGE_DIRECTORY = "/mnt/castle/Images/"
# CLIP_EMBEDDINGS = DATA_DIRECTORY
# DATA_YEARS = ["LSC23"]

# Load CLIP Model
device = "cpu"
if torch.cuda.is_available():  # type: ignore
    device = "cuda"

THRESHOLD = 0.0403

# Detect if the tokenized text is longer than the context length
def _check_context_length(text: str, context_length: int) -> bool:
    tokens = _tokenizer.encode(text)
    if len(tokens) > context_length:
        return False
    return True


# If the tokenized text is longer than the context length, split it into multiple sentences
def _split_text(text: str, context_length: int) -> List[str]:
    sentences = text.split(".")
    result = []
    while sentences:
        sentence = sentences.pop(0)
        while sentences and _check_context_length(
            sentence + "." + sentences[0], context_length
        ):
            sentence += "." + sentences.pop(0)
        result.append(sentence)
    return result


class ClipModel:
    def __init__(self):
        self.name = "clip"
        clip_model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED_DATASET, device=device
        )
        assert isinstance(clip_model, CLIP), "Model is not CLIP"
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)

        self.clip_model = clip_model
        self.preprocess = preprocess
        self.tokenizer = tokenizer

        self.clip_model = self.clip_model.to(device)
        self.clip_model.eval()

        self.features = VIT14_CLIP_FEATURES

    def encode_text(self, main_query: str, normalize: bool = True) -> np.ndarray:
        with torch.no_grad():
            sentences = _split_text(main_query, 77)
            tokens = self.tokenizer(sentences).to(device)
            text_encoded = self.clip_model.encode_text(tokens)  # type: ignore

            if len(sentences) > 1:
                text_encoded = text_encoded.mean(dim=0, keepdim=True)  # type: ignore
            else:
                text_encoded = text_encoded.squeeze(0)
            if normalize:
                text_encoded /= text_encoded.norm(dim=-1, keepdim=True)  # type: ignore

        text_features = text_encoded.cpu().numpy()
        return text_features

    def encode_image(self, image_path: str, data: Data) -> Array1D[np.float32]:
        image_read = PILImage.open(f"{IMAGE_DIRECTORY}/{data}/{image_path}")
        image_tensor = self.preprocess(image_read).unsqueeze(0).to(device)  # type: ignore
        with torch.no_grad():
            image_feat = self.clip_model.encode_image(image_tensor)
            image_feat /= image_feat.norm(dim=-1, keepdim=True)
        return image_feat.cpu().numpy()

    def score_images(
        self, images: List[str] | np.ndarray, encoded_query: np.ndarray, data: Data
    ) -> List[float]:
        try:
            encoded_query /= LA.norm(encoded_query, keepdims=True, axis=-1)
        except TypeError:
            return [0 for _ in images]
        if images:
            if isinstance(images, np.ndarray):
                image_features = self.features[data].embeddings[images]
            else:
                image_features = self.features[data].embeddings[
                    np.array(
                        [
                            self.features[data].image_to_id_map[image]
                            for image in images
                        ]
                    )
                ]
            similarity = image_features @ encoded_query.T  # B x D @ D x 1 = B x 1
            similarity = similarity.reshape(-1)
            similarity[np.where(similarity < 0.1)] = 0
            return similarity.astype("float").tolist()
        return []

    def score_all_images(
        self, query: str, data: Data
    ) -> Tuple[List[float], np.ndarray]:
        encoded_query = self.encode_text(query, normalize=True)
        similarity = self.features[data].embeddings @ encoded_query.T
        similarity = similarity.reshape(-1)
        # similarity[np.where(similarity < 0.1)] = 0
        return similarity.astype("float").tolist(), encoded_query

    def find_similar_images(self, image_path: str, data: Data) -> Array1D:
        encoded_image = self.encode_image(image_path, data)
        similarity = self.features[data].embeddings @ encoded_image.T
        similarity = similarity.reshape(-1)
        # similarity[np.where(similarity < 0.1)] = 0
        return similarity

    def photo_ids(self, data: Data) -> List[str]:
        return self.features[data].ids

    def photo_features(self, data: Data) -> np.ndarray:
        return self.features[data].embeddings

    async def get_lsc25_similarities(
        self,
        data: Data,
        query: SingleQuery,
        exclude: set[int] = set(),
        visual_only: bool = False,
    ) -> np.ndarray:
        # This method should be overridden in subclasses
        raise NotImplementedError("This method should be implemented in subclasses")

def normalize_scores(scores: Array1D[np.float32]) -> Array1D[np.float32]:
    """Normalize scores to the range [0, 1]."""
    if np.max(scores) == np.min(scores):
        return scores
    return (scores - np.min(scores)) / (np.max(scores) - np.min(scores))

class SIGLIP(ClipModel):
    def __init__(self):
        self.name = "siglip"
        model = AutoModel.from_pretrained(
            "google/siglip-so400m-patch14-384",
            device_map=device,
        )
        processor = AutoProcessor.from_pretrained(
            "google/siglip-so400m-patch14-384",
            device_map=device,
        )
        self.model = model
        self.processor = processor

        self.model.eval()
        self.model.to(device)
        self.lsc25_feat_loaded = False
        self.features = SIGLIP_FEATURES

    @timer("load_lsc25_feat")
    def load_lsc25_feat(self):
        # Precompute once for all test queries
        beta = 20
        self.beta = beta
        k = 10000

        # Load the features
        if os.path.exists(f"{CLIP_EMBEDDINGS}/LSC23/QB_norm/all.pkl"):
            self.retrieved_videos, self.normalizing_sum = pickle.load(
                open(f"{CLIP_EMBEDDINGS}/LSC23/QB_norm/all.pkl", "rb")
            )
        else:
            query_features = np.load(
                f"{CLIP_EMBEDDINGS}/LSC23/QB_norm/query_features.npy"
            )
            query_features = query_features / np.linalg.norm(
                query_features, axis=1, keepdims=True
            )

            # Step 1: Precompute with training queries and dataset features
            train_test = query_features @ self.features[Data.LSC23].embeddings.T
            train_test_exp = np.exp(train_test * beta)
            self.retrieved_videos = get_retrieved_videos(train_test_exp, k)
            self.normalizing_sum = np.sum(a=train_test_exp, axis=0)
            with open(f"{CLIP_EMBEDDINGS}/LSC23/QB_norm/all.pkl", "wb") as f:
                pickle.dump((self.retrieved_videos, self.normalizing_sum), f)

        print(
            f"LSC25 features loaded with beta={self.beta}, k={k}, "
            f"retrieved videos shape: {self.retrieved_videos.shape}"
        )

        # Add location features
        location_features = np.load(
            f"{CLIP_EMBEDDINGS}/LSC23/google-siglip-so400m-patch14-384_nonorm/location_features.npy"
        )
        location_features = location_features / LA.norm(
            location_features, keepdims=True, axis=-1
        )

        self.location_features = {
            Data.LSC23: location_features,
            Data.Deakin: None,
        }
        photo_ids = self.features[Data.LSC23].ids
        photo_id_to_index = {
            photo.split("/")[-1].split(".")[0]: i for i, photo in enumerate(photo_ids)
        }
        self.times = get_time_info(photo_ids, photo_id_to_index)

        print(
            f"Location features loaded with shape: {location_features.shape}, "
            f"Time features shape: {len(self.times)}"
        )

        self.lsc25_feat_loaded = True

    def encode_text(self, main_query: str, normalize=False) -> Array1D[np.float32]:
        sentences = _split_text(main_query, 77)
        inputs = self.processor(
            text=sentences,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        inputs.to(device)
        with torch.no_grad():
            with torch.autocast(device):
                outputs = self.model.get_text_features(**inputs).mean(dim=0)
                if normalize:
                    outputs = outputs / outputs.norm(dim=-1, keepdim=True)
        return outputs.cpu().float().numpy()

    def encode_image(self, image_path: str, data: Data) -> Array1D[np.float32]:
        image_read = PILImage.open(f"{IMAGE_DIRECTORY}/{data}/{image_path}")
        inputs = self.processor(
            images=image_read,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        inputs.to(device)
        with torch.no_grad():
            with torch.autocast(device):
                outputs = self.model.get_image_features(**inputs)
                outputs = outputs / outputs.norm(dim=-1, keepdim=True)
        return outputs.cpu().float().numpy()

    @async_timer("get_lsc25_similarities")
    async def get_lsc25_similarities(
        self, data, query: SingleQuery, exclude: set[int] = set(),
        visual_only: bool = False
    ):
        if not self.lsc25_feat_loaded:
            self.load_lsc25_feat()

        encoded_query = self.encode_text(query.full_text, normalize=True)
        # Apply query bank normalization
        similarities = apply_qb_norm_to_query(
            encoded_query,
            self.features[data].embeddings,
            self.retrieved_videos,
            self.normalizing_sum,
            self.beta,
        )
        # similarities[np.where(similarities < THRESHOLD)] = 0
        similarities = normalize_scores(similarities)

        # Apply location and time features if available
        if not visual_only and query.location:
            location = query.location or query.full_text
            # Encode location text
            encoded_location = self.encode_text(location, normalize=True)
            # Location features
            print("[blue]Location sentic search enabled[/blue]")
            location_similarities: Array1D[np.float32] = (
                self.location_features[data] @ encoded_location.T
            )
            location_similarities = location_similarities.reshape(-1)
            # use threshold
            # location_similarities[np.where(location_similarities < THRESHOLD)] = 0

            location_similarities = normalize_scores(location_similarities)
            non_zero_indices = np.where(location_similarities > 0.0)[0]
            if len(non_zero_indices) > 0:
                print(
                    f"[blue]Location similarities found for {len(non_zero_indices)} images[/blue]"
                )
                # normalize similarities so that the maximum value is 1 and the minimum value is 0
                alpha = 0.8
                similarities: Array1D[np.float32] = alpha * similarities + (1 - alpha) * location_similarities
            else:
                print("[blue]No location similarities found[/blue]")

        if not visual_only:
            time_query = f"{query.time} {query.date}".strip()
            time_query = time_query or query.full_text
            # get time heatmap
            matrix = await get_time_heatmap(time_query)
            if matrix is not None:
                probabilities = map_matrix_to_photos(matrix, self.times)
                non_zero_indices = np.where(probabilities > 0.0)[0]
                if len(non_zero_indices) > 0:
                    print("[blue]Time heatmap enabled[/blue]")
                    # Apply probabilities to the similarities
                    similarities = similarities * probabilities
                else:
                    print("[blue]No time heatmap probabilities found[/blue]")

            similarities = normalize_scores(similarities)
            # similarities = np.clip(similarities, 0.0, 1.0)

        if exclude:
            # Apply filters to the similarities
            similarities[np.array(list(exclude))] = 0

        return similarities


clip_model = ClipModel()
siglip_model = SIGLIP()

# clip_model.load_data()
# siglip_model.load_data()
siglip_model.load_lsc25_feat()


def get_model(data: Data):
    if data == Data.LSC23:
        return siglip_model
    elif data == Data.Deakin:
        return siglip_model


def get_model_by_name(name: str):
    if name == "clip":
        return clip_model
    elif name == "siglip":
        return siglip_model
    else:
        raise ValueError(f"Unknown model name: {name}")


def encode_text(*args, chosen_model: ClipModel = siglip_model, **kwargs):
    return chosen_model.encode_text(*args, **kwargs)


def encode_image(*args, chosen_model: ClipModel = siglip_model, **kwargs):
    return chosen_model.encode_image(*args, **kwargs)


def score_images(*args, chosen_model: ClipModel = siglip_model, **kwargs):
    return chosen_model.score_images(*args, **kwargs)


def features(data: Data):
    chosen_model = get_model(data)
    return chosen_model.photo_features(data)


def photo_ids(data: Data):
    chosen_model = get_model(data)
    return chosen_model.photo_ids(data)


print("visual.py loaded")
