import os

import numpy as np
import pandas as pd
from configs import CLIP_EMBEDDINGS
from numpy import linalg as LA
from query_parse.types.requests import Data


def load_features(paths):
    # Load pre-embedded photo features
    photo_features = np.zeros((0, 0))
    photo_ids: np.ndarray = np.array([])
    if not paths:
        return photo_features, {}, []

    for path in paths:
        print(path)
        if not os.path.exists(f"{path}/features.npy"):
            continue
        new_photo_features = np.load(f"{path}/features.npy")
        if photo_features.size == 0:
            photo_features = new_photo_features
        else:
            photo_features = np.concatenate([photo_features, new_photo_features])

        # For photo ids
        new_photo_ids = pd.read_csv(f"{path}/photo_ids.csv")
        if isinstance(new_photo_ids, pd.DataFrame):
            new_photo_ids = new_photo_ids["photo_id"]
            if new_photo_ids is not None:
                photo_ids = np.concatenate([photo_ids, new_photo_ids])

        assert photo_features.shape[0] == len(
            photo_ids
        ), f"Mismatch between photo features and photo ids {photo_features.shape[0]} != {len(photo_ids)}"

    # Normalize photo features
    norm_photo_features = photo_features / LA.norm(
        photo_features, keepdims=True, axis=-1
    )

    list_photo_ids: list[str] = photo_ids.tolist()
    print(list_photo_ids[:10])
    print(
        "day2/Florian/17_866.webp" in list_photo_ids,
        "day2/Florian/17_866.webp" in photo_ids,
    )

    image_to_id = {image: i for i, image in enumerate(list_photo_ids)}
    print(
        f"Loaded {len(list_photo_ids)} photo ids with shape {norm_photo_features.shape}"
    )
    return norm_photo_features, image_to_id, list_photo_ids


class CLIPFeature:
    def __init__(self, paths: list[str]):
        self.paths = paths
        self.loaded = False

    def load(self):
        self.photo_features, self.image_to_id, self.photo_ids = load_features(
            self.paths
        )
        self.loaded = True

    @property
    def embeddings(self):
        if not self.loaded:
            self.load()
        return self.photo_features

    @property
    def ids(self):
        if not self.loaded:
            self.load()
        return self.photo_ids

    @property
    def image_to_id_map(self):
        if not self.loaded:
            self.load()
        return self.image_to_id


SIGLIP_FEATURES = {
    Data.LSC23: CLIPFeature(
        [
            f"{CLIP_EMBEDDINGS}/LSC23/google-siglip-so400m-patch14-384_nonorm",
        ]
    ),
    Data.Deakin: CLIPFeature(
        [
            f"{CLIP_EMBEDDINGS}/Deakin/siglip-so400m-patch14-384",
        ]
    ),
    Data.CASTLE: CLIPFeature(
        [
            f"{CLIP_EMBEDDINGS}/CASTLE/siglip-so400m-patch14-384",
        ]
    ),
}

VIT14_CLIP_FEATURES = {
    Data.LSC23: CLIPFeature([f"{CLIP_EMBEDDINGS}/LSC23/ViT-L-14-336_openai_nonorm"]),
    Data.Deakin: None,
    Data.CASTLE: None,
}

SIGLIP_FEATURES[Data.CASTLE].load()
