from tqdm.auto import tqdm

from database.main import get_db, scene_collection
from query_parse.types.requests import Data
from results.models import Image
from visual.segments import get_keyframes_from_segments

def insert_keyframes(data: Data):
    db = get_db(data)
    for scene in tqdm(scene_collection(db).find()):
        images = scene["images"]
        images = [Image.model_validate(image) for image in images]
        keyframes = get_keyframes_from_segments(None, data, images)
        keyframes = [keyframe.model_dump() for keyframe in keyframes]
        scene_collection(db).update_one({"_id": scene["_id"]}, {"$set": {"keyframes": keyframes}})





