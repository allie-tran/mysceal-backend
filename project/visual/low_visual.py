from pandas.io.formats.style import pd
from configs import CLIP_EMBEDDINGS, DATA_DIRECTORY
from query_parse.types.requests import Data
import os
import numpy as np


paths = {
    Data.LSC23: f"{CLIP_EMBEDDINGS}/{Data.LSC23}/google-siglip-so400m-patch14-384_nonorm",
    Data.Deakin: f"{CLIP_EMBEDDINGS}/{Data.Deakin}/siglip-so400m-patch14-384",
    Data.CASTLE: f"{CLIP_EMBEDDINGS}/{Data.CASTLE}/siglip-so400m-patch14-384",
}

def get_duplicates(data: Data):
    duplicates: set[str] = set()
    if os.path.exists(f"{DATA_DIRECTORY}/{data}/duplicates.txt"):
        with open(f"{DATA_DIRECTORY}/{data}/duplicates.txt") as f:
            duplicates = f.readlines()
        duplicates = [line.strip() for line in duplicates]
        duplicates = set(duplicates)
    return duplicates


def get_low_visual_density_indices(data: Data):
    photo_ids = pd.read_csv(f"{paths[data]}/photo_ids.csv")["photo_id"].tolist()
    try:
        low_density_df = pd.read_csv(f"{CLIP_EMBEDDINGS}/{data}/visual_density.csv")
        low_density_images = low_density_df[low_density_df["score"] < 5]["image"].tolist()
        low_density_images = set(low_density_images)

        duplicates = get_duplicates(data)
        low_density = [
            (i, image)
            for i, image in enumerate(photo_ids)
            if image in low_density_images or image.split("/")[-1] in duplicates
        ]
        low_density_indices, low_density_photos = zip(*low_density)
    except FileNotFoundError:
        print(f"Visual density file not found for {data}. Returning empty sets.")
        return set(), set(), set(range(len(photo_ids)))
    return set(low_density_photos), set(low_density_indices), set(range(len(photo_ids))) - set(low_density_indices)

print("Generating low visual density indices...")
blurred = {}
blurred_indices = {}
np_blurred_indices = {}
clear_indices = {}

for data in [Data.LSC23, Data.Deakin, Data.CASTLE]:
    blurred[data], blurred_indices[data], clear_indices[data] = get_low_visual_density_indices(data)
    np_blurred_indices[data] = np.array(list(blurred_indices[data]), dtype=np.int32)

print("Low visual density indices generated.")
