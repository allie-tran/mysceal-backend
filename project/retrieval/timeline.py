import traceback
from datetime import datetime, timedelta
from typing import List, Optional

from database.main import get_db, group_collection, image_collection, scene_collection
from pydantic import validate_call
from query_parse.types.requests import Data
from results.models import (
    HighlightItem,
    Image,
    TimelineGroup,
    TimelineResult,
    TimelineScene,
)
from visual.segments import get_keyframes_from_segments, presegments


def get_timeline(image: str, data: Data = Data.LSC23) -> Optional[TimelineResult]:
    """
    For a given image, get the timeline of the group it belongs to
    The start of timeline is the start of the first group of the day,
    or the last group of the previous day if it lasts over midnight

    The end of timeline is the end of the last group of the day,
    or the first group of the next day if it lasts over midnight
    """
    print("Getting image info")
    db = get_db(data)

    try:
        image_info = image_collection(db).find_one({"image": image})
        if not image_info:
            return None

        highlight = HighlightItem(**image_info)
        match data:
            case Data.LSC23:
                image_date = image_info["time"]
            case Data.CASTLE:
                image_date = image_info["utc_time"]
            case Data.Deakin:
                image_date = image_info["snap"]["utc_time"]

        start_time = image_date.replace(hour=0, minute=0, second=0)
        end_time = image_date.replace(hour=23, minute=59, second=59)

        if data == Data.LSC23:
            # Get all groups of the same day
            group_ids = group_collection(db).find(
                {
                    "$or": [
                        {"start_time": {"$gte": start_time, "$lte": end_time}},
                        {"end_time": {"$gte": start_time, "$lte": end_time}},
                    ]
                },
                {"group": 1},
            )
            group_range_ids: List[str] = [group["group"] for group in group_ids]
            print("Getting scenes for group ids")
            results = get_scene_for_group_ids(group_range_ids)
            print("OK")
            return TimelineResult(date=start_time, result=results, highlight=highlight)
        elif data == Data.CASTLE:
            start_time = image_date - timedelta(minutes=10)
            end_time = image_date + timedelta(minutes=10)
            person = image_info["person"]
            images = image_collection(db).find(
                {"person": person, "utc_time": {"$gte": start_time, "$lte": end_time}},
                {"image": 1, "utc_time": 1, "person": 1},
            )
            photo_to_segment_id = presegments[data].photo_to_segment_id
            events = presegments[data].events
            segments = []
            used_segments = set()
            for photo in images:
                segment_id = photo_to_segment_id.get(photo["image"])
                if segment_id:
                    if segment_id in used_segments:
                        continue

                    segments.append(events[segment_id])
                    used_segments.add(segment_id)

            results = []
            highlight = HighlightItem(image=image, scene="", group="")
            for i, event in enumerate(segments):
                day = event.start_time.strftime("%d")
                start = event.start_time.strftime("%H:%M")
                end = event.end_time.strftime("%H:%M")
                person = event.user_id
                time_info = f"day{day}. {start} - {end}"
                images = set(i["image"] for i in event.images)
                if image in images:
                    highlight.group = str(i)
                    highlight.scene = str(i)
                results.append(
                    TimelineGroup(
                        time_info=[time_info],
                        group=str(i),
                        scenes=[
                            TimelineScene(
                                scene=str(i),
                                images=event.images,
                                keyframes=get_keyframes_from_segments(
                                    None, data, event.images
                                ),
                            )
                        ],
                        location=person,
                        location_info=f"day{day}",
                    )
                )
            return TimelineResult(date=start_time, result=results, highlight=highlight)
        elif data == Data.Deakin:
            raise NotImplementedError("Deakin data not implemented yet")
    except Exception:
        traceback.print_exc()


@validate_call
def get_scene_for_group_ids(
    group_range_ids: List[str], data: Data = Data.LSC23
) -> List[TimelineGroup]:
    db = get_db(data)
    grouped_results = scene_collection(db).aggregate(
        [
            {"$match": {"group": {"$in": group_range_ids}}},
            {"$sort": {"start_time": 1, "group": 1, "scene": 1}},
            {
                "$group": {
                    "_id": "$group",
                    "group": {"$first": "$group"},
                    "scenes": {"$push": "$scene"},
                    "images": {"$push": "$images"},
                    "keyframes": {"$push": "$keyframes"},
                    "time_info": {"$push": "$time_info"},
                    "location": {"$first": "$location"},
                    "location_info": {"$first": "$location_info"},
                }
            },
            {"$sort": {"group": 1}},
        ]
    )

    results: List[TimelineGroup] = []
    for group in grouped_results:
        scenes: List[TimelineScene] = []

        for scene, images, keyframes in zip(
            group["scenes"], group["images"], group["keyframes"]
        ):
            images = [Image.model_validate(image) for image in images]
            keyframes = [Image.model_validate(keyframe) for keyframe in keyframes]
            scenes.append(
                TimelineScene(scene=scene, images=images, keyframes=keyframes)
            )

        group["scenes"] = scenes
        group_obj = TimelineGroup(**group)
        results.append(group_obj)
    return results


@validate_call
def get_timeline_for_date(
    str_date: str, data: Data = Data.LSC23
) -> Optional[TimelineResult]:
    """
    Get all scenes for a given date
    Exclude the images that are not in the keep_only list
    """
    db = get_db(data)
    date = datetime.strptime(str_date, "%d-%m-%Y")
    start_time = date.replace(hour=0, minute=0, second=0)
    end_time = date.replace(hour=23, minute=59, second=59)

    # Get all groups of the same day
    group_ids = group_collection(db).find(
        {
            "$or": [
                {"start_time": {"$gte": start_time, "$lte": end_time}},
                {"end_time": {"$gte": start_time, "$lte": end_time}},
            ]
        },
        {"group": 1},
    )

    group_range_ids = [group["group"] for group in group_ids]
    results = get_scene_for_group_ids(group_range_ids)
    return TimelineResult(date=start_time, result=results)
