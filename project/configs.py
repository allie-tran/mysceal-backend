"""
Configs for the project
"""

from datetime import datetime
import os

from dotenv import load_dotenv

load_dotenv()
from joblib import Memory

memory = Memory(location="cache", verbose=0)

# ====================== #
# General Customisation  #
# ====================== #
# These could be adjusted in the frontend with settings
DEV_MODE = False
USE_GROQ = False
DEBUG = False
CACHE = False

# Search Configurations
# ------------------- #
# Default search size
DEFAULT_SIZE = 500

# LLM Configurations
# ---------------- #
# Whether to parse the query or not with the LLM model
QUERY_PARSER = True

# Whether to use the LLM for relevant fields or not
FILTER_FIELDS = True

# Maximum number of images per event (0 for no limit)
MAX_IMAGES_PER_EVENT = 25

# Whether to merge events based on the relevant fields
MERGE_EVENTS = True
MAXIMUM_EVENT_TO_GROUP = 20
WINDOW_SIZE = 500

RERANK = False

# QA Configurations
BUILD_ON_STARTUP = True

# ==================== #
# Model Configurations #
# ==================== #

# CLIP model configurations
FORCE_CPU = False
MODEL_NAME = "ViT-L-14-336"  # or ViT-H-14
PRETRAINED_DATASET = "openai"  # or laion2b_s32b_b79k
CLIP_EMBEDDINGS = os.environ.get("CLIP_EMBEDDINGS")
# ==================== #

# ====================== #
# Dataset Configurations #
# ====================== #
DATA_YEARS = ["LSC23"]
FILES_DIRECTORY = os.getenv("FILES_DIRECTORY")
IMAGE_DIRECTORY = os.getenv("IMAGE_DIRECTORY", "images")
DATA_DIRECTORY = os.environ.get("DATA_DIRECTORY")
# ====================== #
# Elasticsearch Configurations #
# ====================== #
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", 9200)
ES_URL = f"http://{ES_HOST}:{ES_PORT}"

IMAGE_INDEX = os.getenv("INDEX", "all_lsc")
SCENE_INDEX = os.getenv("SCENE_INDEX", "all_lsc_mean")

# ========================== #
# Functions to derive fields #
# ========================== #
ESSENTIAL_FIELDS = ["images", "scene", "group", "start_time", "end_time", "gps", "time", "local_time", "timezone"]

IMAGE_ESSENTIAL_FIELDS = [
    "snap",
    "image",
    "time",
    "gps",
    "scene",
    "group",
    "location",
    "aspect_ratio",
    "hash_code",
    "local_time",
    "icon",
    "timezone",
    "person"
]

DEPENDENCIES = {"place": ["location"], "place_info": ["location"]}

DERIVABLE_FIELDS = {
    "time": lambda x: x.start_time,
    "minute": lambda x: x.start_time.strftime("%H:%M"),
    "hour": lambda x: x.start_time.strftime("%H %p"),
    "day": lambda x: x.start_time.strftime("%d"),
    "date": lambda x: x.start_time.strftime("%d-%m-%Y"),
    "week": lambda x: x.start_time.isocalendar()[1],
    "duration": lambda x: (x.end_time - x.start_time).seconds,
    "weekday": lambda x: x.start_time.strftime("%A"),
    "month": lambda x: x.start_time.strftime("%B %Y"),
    "year": lambda x: x.start_time.year,
    "city": lambda x: [r for r in x.region if r != x.country],
    "days": lambda x: (x.end_time - x.start_time).days,
    "hours": lambda x: (x.end_time - x.start_time).seconds // 3600,
    "weeks": lambda x: (x.end_time - x.start_time).days // 7,
    "place": lambda x: x.location,
    "place_info": lambda x: x.location_info,
}


def get_city_equal(x, y):
    if not x or not y:
        return x == y
    return set(x).intersection(set(y))


ISEQUAL = {"*": lambda x, y: x == y, "city": get_city_equal}
# Fields in ORDER in the textual description
TIME_FIELDS = [
    "minute",
    "hour",
    "start_time",
    "end_time",
    "weekday",
    "date",
    "week",
    "month",
    "year",
]
LOCATION_FIELDS = ["location", "location_info", "city", "region", "country", "address"]
DURATION_FIELDS = ["months", "weeks", "days", "hours", "minutes"]
VISUAl_FIELDS = ["images", "ocr"]
EXCLUDE_FIELDS = [
    "images",
    "gps",
    "scene",
    "group",
    "start_time",
    "end_time",
    "timestamp",
    "ocr",
]

SORT_VALUES = {
    "date": lambda x: datetime.strptime(x, "%d-%m-%Y"),
    "month": lambda x: datetime.strptime(x, "%B %Y"),
    "weekdays": lambda x: datetime.strptime(x, "%A"),
    "hour": lambda x: datetime.strptime(x, "%H %p"),
    "year": lambda x: int(x),
    "duration": lambda x: int(x),
}
# ====================== #
# QA Configurations #
# ====================== #

PRETRAINED_MODELS = os.environ.get("PRETRAINED_MODELS")
QA_FEATURES = [
    f"{CLIP_EMBEDDINGS}/LSC23/ViT-L-14_openai_nonorm/features.npy",
    f"{CLIP_EMBEDDINGS}/LSC20/ViT-L-14_openai_nonorm/features.npy",
]
QA_IDS = [
    f"{CLIP_EMBEDDINGS}/LSC23/ViT-L-14_openai_nonorm/photo_ids.csv",
    f"{CLIP_EMBEDDINGS}/LSC20/ViT-L-14_openai_nonorm/photo_ids.csv",
]
QA_DIM = 768

QA_OPTIONS = [
    "frozenbilm_activitynet",
    "frozenbilm_tgif",
    "frozenbilm_msrvtt",
    "frozenbilm_msvd",
    "frozenbilm_tvqa",
]

QA_PATH = f"{PRETRAINED_MODELS}/models/FrozenBiLM/{QA_OPTIONS[0]}.pth"
MSRVTT_VOCAB_PATH = f"{PRETRAINED_MODELS}/datasets/MSRVTT-QA/vocab.json"
VOCAB_PATH = f"{FILES_DIRECTORY}/backend/all_answers.csv"
QA_LLM_BASE = "microsoft/deberta-v2-xlarge"

TEXT_QA_MODEL_OPTIONS = [
    "models/question-answering__deepset--roberta-base-squad2",
    "models/bert-large-uncased-whole-word-masking-finetuned-squad",
]

TEXT_QA_MODEL = TEXT_QA_MODEL_OPTIONS[1]

JSON_START_FLAG = "```json"
JSON_END_FLAG = "```"

# ====================== #
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# ====================== #
# MongoDB Configurations #
# ====================== #
# EXPIRE_TIME = 60 * 60 * 24 * 7  # 1 week
EXPIRE_TIME = 60 * 5  # 5 minutes

# ====================== #
# Submitting to DRES
# ====================== #
DRES_URL = "https://vbs.videobrowsing.org/"
DRES_API_URL = f"{DRES_URL}/api/v2"
LOGIN_URL = f"{DRES_API_URL}/login"
LOGOUT_URL = f"{DRES_API_URL}/logout"
SUBMIT_URL = f"{DRES_API_URL}/submit"
