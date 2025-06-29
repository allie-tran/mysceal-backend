import json
from datetime import datetime

from configs import FILES_DIRECTORY
from database.main import get_db, image_collection 
from query_parse.types.requests import Data

time_info = json.load(open(f"{FILES_DIRECTORY}/backend/time_info.json"))


def get_dict(image: str, data: Data = Data.LSC23) -> dict:
    if "/" not in image:
        image = f"{image[:6]}/{image[6:8]}/{image}"
    db = get_db(data)
    info = image_collection(db).find_one({"image": image})
    assert info, f"Image {image} not found"
    return info


def get_display_info(scenes, best_scene, query_info):
    location = scenes[0]["country"]
    if scenes[0]["location"] != "---":
        to_show = []
        if "regions" in query_info:
            to_show = [
                region
                for region in scenes[0]["region"]
                if region.lower() in query_info["regions"]
                and region != scenes[0]["country"]
            ]
        if to_show:
            location = (
                scenes[0]["location"] + f", " + ", ".join(to_show) + f" ({location})"
            )
        else:
            location = scenes[0]["location"] + f" ({location})"

    return [
        location,
        datetime.strftime(scenes[0]["start_time"], "%A, %d/%m/%Y"),
        time_info[best_scene],
    ]
