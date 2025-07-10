# import os
# from typing import List, Tuple

# import numpy as np
# import open_clip
# import pandas as pd
# import torch
# from configs import (
#     CLIP_EMBEDDINGS,
#     DATA_DIRECTORY,
#     DATA_YEARS,
#     EMBEDDING_DIM,
#     IMAGE_DIRECTORY,
#     MODEL_NAME,
#     PRETRAINED_DATASET,
# )
# from numpy import linalg as LA
# from open_clip.model import CLIP
# from open_clip.tokenizer import _tokenizer
# from PIL import Image as PILImage
# from retrieval.async_utils import timer
# from retrieval.temporal_feat_extract import (
#     get_time_heatmap,
#     get_time_info,
#     map_matrix_to_photos,
# )
# from rich import print
# from transformers import AutoModel, AutoProcessor

# from query_parse.types.requests import Data

from .constants import DESCRIPTIONS
from .types.elasticsearch import VisualInfo
from .utils import search_keywords

def search_for_visual(text: str) -> VisualInfo:
    """
    Search for visual information
    """
    concepts = search_keywords(DESCRIPTIONS, text)
    visual_info = VisualInfo(
        text=text,
        concepts=concepts,
    )
    return visual_info
