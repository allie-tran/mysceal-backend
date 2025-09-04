import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from zoneinfo import ZoneInfo

from configs import ESSENTIAL_FIELDS, IMAGE_ESSENTIAL_FIELDS
from geopy.geocoders import Nominatim
from llm import llm_model
from llm.prompt.organize import RELEVANT_FIELDS_PROMPT
from myeachtra.dependencies import memory
from pydantic import ValidationError
from pydantic.alias_generators import to_camel
from query_parse.types.elasticsearch import GPS
from query_parse.types.lifelog import RelevantFields
from query_parse.types.requests import ChoicesResponse, Data, MapRequest
from query_parse.utils import extend_no_duplicates
from results.models import AsyncioTaskResult, Event, Icon, Image, Marker
from retrieval.async_utils import async_timer
from rich import print as rprint

import requests
from database.main import (
    get_db,
    image_collection,
    location_collection,
    scene_collection,
)


def to_event(data: Data, image: dict) -> Event:
    if "start_time" in image:
        return Event(**image)
    try:
        if data == Data.Deakin:
            image["time"] = image["snap"]["local_time"]
        elif data == Data.CASTLE:
            image["time"] = image["local_time"]

        image["start_time"] = image.pop("time")
        image["end_time"] = image["start_time"]
        timezone = image.pop("timezone", "UTC")
        image["timezone"] = timezone
        image["start_time"] = image["start_time"].astimezone(ZoneInfo(timezone))
        image["end_time"] = image["end_time"].astimezone(ZoneInfo(timezone))

        image["images"] = [
            Image(
                src=image.pop("image"),
                aspect_ratio=image.pop("aspect_ratio"),
                hash_code=image.pop("hash_code"),
            )
        ]

        if "gps" in image:
            image["gps"] = [GPS(**image.pop("gps"))]
        else:
            # For deakin
            image["gps"] = []

        if "icon" in image:
            image["icon"] = Icon(**image.pop("icon"))

        if "patient" in image:
            image["user_id"] = image["patient"]["id"]

        if "person" in image:
            image["user_id"] = image["person"]

        return Event(**image, data=data)
    except KeyError as e:
        print(image)
        raise e


def convert_to_events(
    key_list: List[str],
    relevant_fields: Optional[List[str]] = None,
    key: Literal["scene", "image"] = "scene",
    data: Data = Data.LSC23,
) -> List[Event]:
    """
    Convert a list of event ids to a list of Event objects
    """
    db = get_db(data)

    collection = scene_collection if key == "scene" else image_collection
    fields = ESSENTIAL_FIELDS if key == "scene" else IMAGE_ESSENTIAL_FIELDS
    if data == Data.Deakin:
        fields = [field for field in fields if field != "location"]

    documents = []
    index = {key: i for i, key in enumerate(key_list)}
    if relevant_fields:
        projection = extend_no_duplicates(relevant_fields, fields)
        try:
            documents = collection(db).find(
                {key: {"$in": key_list}}, projection=projection
            )
        except Exception as e:
            rprint("[red]Error in convert_to_events[/red]", e)

    if not documents:
        documents = collection(db).find({key: {"$in": key_list}}, projection=fields)

    # Sort the documents based on the order of the event_list
    documents = sorted(documents, key=lambda doc: index[doc[key]])

    events = []
    if key == "scene":
        events = [Event(**doc, data=data) for doc in documents]
    else:
        events = [to_event(data, doc) for doc in documents]

    for event in events:
        event.markers, event.orphans = calculate_markers(event)
    return events


def image_src_to_image_object(images: List[str], data: Data) -> List[Image]:
    db = get_db(data)
    documents = image_collection(db).find({"image": {"$in": images}})
    docs = {
        doc["image"]: Image(
            src=doc["image"],
            aspect_ratio=doc["aspect_ratio"],
            hash_code=doc["hash_code"],
        )
        for doc in documents
    }
    return [docs[image] for image in images if image in docs]


def segment_to_event(
    data: Data,
    images: List[str],
) -> Event | None:
    """
    Convert a list of images and scores to an Event object
    """
    db = get_db(data)
    documents = image_collection(db).find(
        {"image": {"$in": images}}, projection=IMAGE_ESSENTIAL_FIELDS
    )
    image_to_doc = {doc["image"]: doc for doc in documents}
    images = [img for img in images if img in image_to_doc]

    if not image_to_doc:
        print(f"No images found in the database for {images}")
        return None

    main_image = image_to_doc[images[0]]
    event = to_event(data, main_image)

    if len(images) > 1:
        rest_images = [image_to_doc[img] for img in images[1:] if img in image_to_doc]
        rest_events = [to_event(data, img) for img in rest_images]
        event.merge_with_many(1, rest_events, [1] * len(rest_events))

    event.markers, event.orphans = calculate_markers(event)
    return event


def segments_to_events(
    data: Data,
    segments: Union[List[Tuple[int, int]], List[List[str]]],
    scores: None | List[float] | List[int],
    photo_ids: List[str],
    relevant_fields: Optional[List[str]] = None,
) -> List[Event]:
    """
    Convert the segments to events
    """
    db = get_db(data)
    images = []
    for segment in segments:
        if isinstance(segment, list) and isinstance(segment[0], str):
            images.extend(segment)
        else:
            start, end = segment
            images.extend(photo_ids[start:end])
    documents = []

    if relevant_fields:
        projection = extend_no_duplicates(relevant_fields, IMAGE_ESSENTIAL_FIELDS)
        try:
            documents = image_collection(db).find(
                {"image": {"$in": images}}, projection=projection
            )
        except Exception as e:
            rprint("[red]Error in convert_to_events[/red]", e)

    if not documents:
        documents = image_collection(db).find(
            {"image": {"$in": images}}, projection=IMAGE_ESSENTIAL_FIELDS
        )
    image_to_doc = {doc["image"]: doc for doc in documents}

    # DEBUG: print images not found in the database
    not_found_images = [img for img in images if img not in image_to_doc]

    if not_found_images:
        rprint("[red]Images not found in the database:[/red]", len(not_found_images))

    events = []
    if scores is None:
        scores = [1.0] * len(segments)
    for segment, score in zip(segments, scores):
        images = []
        if isinstance(segment, list) and isinstance(segment[0], str):
            images = segment
        else:
            start, end = segment
            images = photo_ids[start:end]
        event_images = [photo for photo in images if photo in image_to_doc]
        if not event_images:
            continue
        event = to_event(data, image_to_doc[event_images[0]])
        if len(event_images) > 1:
            rest = [
                to_event(data, image_to_doc[photo_id]) for photo_id in event_images[1:]
            ]
            event.merge_with_many(score, rest, [score] * len(rest))
        events.append(event)

    if data == Data.LSC23:
        for event in events:
            event.markers, event.orphans = calculate_markers(event)

    return events


def get_event_from_images(images: List[str], data: Data) -> Event:
    db = get_db(data)
    documents = image_collection(db).find({"image": {"$in": images}})
    docs = [to_event(data, doc) for doc in documents]
    if len(docs) == 1:
        return docs[0]
    event = docs[0]
    event.merge_with_many(1, docs[1:], [1] * len(docs[1:]))
    return event


def calculate_markers(event: Event) -> Tuple[List[Marker], List[GPS]]:
    """
    Calculate the markers for one event, straight from the mongo document
    """
    if event.location:
        markers = [
            Marker(
                location=event.location,
                points=event.gps,
                location_info=event.location_info,
                icon=event.icon,
            )
        ]
        return markers, []
    return [], event.gps


@async_timer("get_relevant_fields")
async def get_relevant_fields(data: Data, query: str, tag: str) -> AsyncioTaskResult:
    """
    Get the relevant fields from the query
    """
    prompt = RELEVANT_FIELDS_PROMPT.format(query=query)
    fields = {}
    while True:
        try:
            res = llm_model.generate_from_text(data, prompt)
            if res:
                rprint("Relevant Fields", fields)
                fields = res
                break
        except ValidationError as e:
            rprint(e)

    relevant_fields = RelevantFields.model_validate(fields)
    return AsyncioTaskResult(results=relevant_fields, tag=tag, task_type="llm")


headers = {
    "accept": "application/json",
    "Authorization": os.getenv("FOURSQUARE_API_KEY"),
}


@memory.cache
def search_fourspace(location: str, lat: float, lng: float) -> str:
    lat = round(lat, 6)
    lng = round(lng, 6)
    url = (
        f"https://api.foursquare.com/v3/places/search?query={location}&ll={lat}%2C{lng}"
    )
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        rprint(f"Error in {location}")
        return ""
    data = response.json()["results"]
    if not data:
        rprint(f"No data for {location}")
        return ""
    return data[0]["fsq_id"]


# Get the location info
@memory.cache
def get_info(fsq_id: str) -> dict:
    url = f"https://api.foursquare.com/v3/places/{fsq_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        rprint(f"Error in {fsq_id}")
        return {}
    data = response.json()
    return data


def calculate_distance(point1: GPS, point2: GPS) -> float:
    """
    Calculate the distance between two points
    """
    return ((point1.lat - point2.lat) ** 2 + (point1.lon - point2.lon) ** 2) ** 0.5


def get_location_name(
    request: MapRequest, data: Data = Data.LSC23
) -> Tuple[str, Optional[GPS]]:
    db = get_db(data)
    location = request.location
    if location == "---":
        location = None

    if location and request.center:
        return location, request.center

    if request.image:
        doc = image_collection(db).find_one({"image.src": request.image})
        if doc:
            return doc["location"], GPS(**doc["gps"])

    scene = scene_collection(db).find_one(
        {
            "$or": [
                {"images": {"$elemMatch": {"src": request.image}}},
                {"scene": request.scene},
                {"group": request.group},
            ]
        }
    )
    if scene:
        points = [GPS(**point) for point in scene["gps"]]
        if len(points) == 1:
            return scene["location"], points[0]
        if points:
            return scene["location"], GPS(
                lat=sum(point.lat for point in points) / len(points),
                lon=sum(point.lon for point in points) / len(points),
            )
        else:
            return scene["location"], request.center

    raise ValueError("No location found")


def get_image_center(image: str, data: Data = Data.LSC23) -> Optional[GPS]:
    db = get_db(data)
    doc = image_collection(db).find_one({"image.src": image})
    if doc:
        return GPS(**doc["gps"])
    return None


def get_location_info(
    request: MapRequest, data: Data = Data.LSC23
) -> Optional[Tuple[str, dict]]:
    """
    Get the location info
    If there is only one location with the same name, return that
    If there are multiple locations with the same name, then check other parameters
    """
    location, center = get_location_name(request)
    if not location or location == "---":
        return "---", {
            "location": location,
            "location_info": "",
            "fsq_id": "",
            "fsq_info": {},
            "gps": center.model_dump() if center else request.center,
            "icon": None,
        }

    db = get_db(data)
    locations = location_collection(db).find({"location": location})
    locations = list(locations)

    info = None
    location_info = ""

    if len(locations) == 1:
        return location, locations[0]
    elif len(locations) > 1:
        if not center:
            for loc in locations:
                if loc["gps"]:
                    return location, loc
        else:
            threshold = 0.01  # 0.1 degrees is about 11 km
            closest_location = None
            closest_distance = float("inf")
            for loc in locations:
                distance = calculate_distance(center, loc["gps"])
                if distance < threshold:
                    return loc
                if distance < closest_distance:
                    closest_location = loc
                    closest_distance = distance
            if closest_location:
                return location, closest_location

    if not center:
        return None
    # Search for the location
    id = search_fourspace(location, center.lat, center.lon)
    if not id:
        return None
    info = get_info(id)
    location_info = ""
    if info["categories"]:
        location_info = info["categories"][0]["name"]

    icon = get_icon_from_fsq(info)
    if not icon:
        icon = get_icon_from_location_name(location, location_info)

    loc = {
        "location": location,
        "location_info": location_info,
        "fsq_id": id,
        "fsq_info": info,
        "gps": center.model_dump(),
        "icon": icon.model_dump() if icon else None,
    }

    location_collection(db).insert_one(
        loc,
    )
    return location, loc


def get_icon_from_fsq(info: dict) -> Optional[Icon]:
    if info and info["categories"]:
        return Icon(
            type="foursquare",
            **info["categories"][0]["icon"],
            name=info["categories"][0]["name"],
        )
    return None


def get_icon_from_location_name(location: str, location_info: str) -> Optional[Icon]:
    match (location.lower(), location_info.lower()):
        case ("home", _):
            return Icon(type="material", prefix="home", name="Home")
        case ("work", _):
            return Icon(type="material", prefix="work", name="Work")
        case (x, _) if "dcu" in x:
            return Icon(type="material", prefix="work", name="Work")
        case (_, x) if "restaurant" in x or "cafe" in x:
            return Icon(type="material", prefix="restaurant", name="Restaurant")
        case (_, x) if "bar" in x:
            return Icon(type="material", prefix="local_bar", name="Bar")
        case (_, x) if "hotel" in x:
            return Icon(type="material", prefix="hotel", name="Hotel")
        case (_, x) if "museum" in x:
            return Icon(type="material", prefix="museum", name="Museum")
        case (_, x) if "park" in x:
            return Icon(type="material", prefix="park", name="Park")
        case (_, x) if "school" in x:
            return Icon(type="material", prefix="school", name="School")
        case (_, x) if "hospital" in x:
            return Icon(type="material", prefix="local_hospital", name="Hospital")
        case (_, x) if "store" in x:
            return Icon(type="material", prefix="store", name="Store")
        case (_, x) if "gym" in x:
            return Icon(type="material", prefix="fitness_center", name="Gym")
        case (_, x) if "pharmacy" in x:
            return Icon(type="material", prefix="local_pharmacy", name="Pharmacy")
        case (_, x) if "bank" in x:
            return Icon(type="material", prefix="local_atm", name="Bank")
        case (_, x) if "library" in x:
            return Icon(type="material", prefix="local_library", name="Library")
        case (_, x) if "university" in x:
            return Icon(type="material", prefix="school", name="University")
        case (_, x) if "airport" in x:
            return Icon(type="material", prefix="local_airport", name="Airport")
        case (_, x) if "train" in x:
            return Icon(type="material", prefix="train", name="Train station")
        case (_, x) if "bus" in x:
            return Icon(type="material", prefix="directions_bus", name="Bus station")
        case (_, x) if "subway" in x:
            return Icon(
                type="material", prefix="directions_subway", name="Subway station"
            )
        case (_, x) if "taxi" in x:
            return Icon(type="material", prefix="local_taxi", name="Taxi stand")
        case (_, x) if "car" in x:
            return Icon(type="material", prefix="local_car_wash", name="Car wash")
        case (_, x) if "gas" in x:
            return Icon(type="material", prefix="local_gas_station", name="Gas station")
        case (_, x) if "parking" in x:
            return Icon(type="material", prefix="local_parking", name="Parking")
        case (_, x) if "church" in x:
            return Icon(type="material", prefix="church", name="Church")
        case (_, x) if "mosque" in x:
            return Icon(type="material", prefix="mosque", name="Mosque")
        case (_, x) if "synagogue" in x:
            return Icon(type="material", prefix="synagogue", name="Synagogue")
        case (_, x) if "temple" in x:
            return Icon(type="material", prefix="temple", name="Temple")
        case (_, x) if "cemetery" in x:
            return Icon(type="material", prefix="cemetery", name="Cemetery")
        case (_, x) if "beach" in x:
            return Icon(type="material", prefix="beach_access", name="Beach")
        case (_, x) if "mountain" in x:
            return Icon(type="material", prefix="terrain", name="Mountain")
        case (_, x) if "lake" in x:
            return Icon(type="material", prefix="water", name="Lake")
        case (_, x) if "river" in x:
            return Icon(type="material", prefix="water", name="River")
        case (_, x) if "sea" in x:
            return Icon(type="material", prefix="water", name="Sea")
        case (_, x) if "ocean" in x:
            return Icon(type="material", prefix="water", name="Ocean")
        case (_, x) if "pool" in x:
            return Icon(type="material", prefix="pool", name="Pool")
        case (_, x) if "stadium" in x:
            return Icon(type="material", prefix="stadium", name="Stadium")
        case (_, x) if "theater" in x:
            return Icon(type="material", prefix="theaters", name="Theater")
        case _:
            return Icon(type="material", prefix="location_on", name="Location icon")


def get_icon(marker: Marker) -> Optional[Icon]:
    """
    Get the icon for the marker
    """
    fsq_info = get_location_info(marker.location, marker.center)  # type: ignore
    if fsq_info and fsq_info["fsq_info"]:  # type: ignore
        return get_icon_from_fsq(fsq_info["fsq_info"])  # type: ignore
    return get_icon_from_location_name(marker.location, marker.location_info)


def get_all_images_with_location(location: str, data: Data = Data.LSC23) -> List[str]:
    db = get_db(data)
    images = image_collection(db).find({"location": location})
    return [image["image"] for image in images]


def get_all_images_from_same_scene(image: str, data: Data = Data.LSC23) -> List[Image]:
    db = get_db(data)
    scene = scene_collection(db).find_one({"images": {"$elemMatch": {"src": image}}})
    if scene:
        return [Image(**img) for img in scene["images"]]
    return []


geolocator = Nominatim(user_agent="myeachtra")


def reverse_geomapping(center: GPS) -> Optional[str]:
    location = geolocator.reverse((center.lat, center.lon), exactly_one=True, language="en")  # type: ignore
    print(location)
    if location:
        return location.address  # type: ignore
    return None


def get_full_data(images: List[str], data: Data) -> Dict[str, Dict[str, Any]]:
    """
    Get the full data for the images
    """
    db = get_db(data)
    image_data = image_collection(db).find({"image": {"$in": images}})
    # Change key cases to camel case
    image_data = [
        {to_camel(key): value for key, value in image.items()} for image in image_data
    ]
    image_data = {image["image"]: image for image in image_data}
    # remove object id
    for image in image_data.values():
        image.pop("_id")
    return image_data


def get_unique_values(
    data: Data, field: str, condition: Optional[dict[str, Any]] = None
) -> List[str]:
    """
    Get the unique values for a field
    """
    db = get_db(data)
    if condition:
        values = image_collection(db).distinct(field, condition)
    else:
        values = image_collection(db).distinct(field)
    return values


def get_unique_patient_ids():
    db = get_db(Data.Deakin)
    # get all unique patientIds along with number of dates
    values = image_collection(db).aggregate(
        [
            {"$group": {"_id": "$patient.id", "dates": {"$addToSet": "$date"}}},
            {"$project": {"patientId": "$_id", "dates": {"$size": "$dates"}}},
            {"$sort": {"patientId": 1}},
        ]
    )
    values = list(values)
    choices = [value["patientId"] for value in values]
    annotations = [f"{value['patientId']} ({value['dates']} dates)" for value in values]
    return ChoicesResponse(choices=choices, annotations=annotations)


def get_segment_counts_per_date(
    patient_id: str | None = None,
) -> dict[str, tuple[int, int]]:
    match_stage = {}
    if patient_id:
        match_stage["patient_id"] = patient_id
    pipeline = [
        {"$match": {"patient_id": patient_id}} if patient_id else {},
        {
            "$project": {
                "date": 1,
                "segment_count": {"$size": {"$ifNull": ["$segments", []]}},
                "eating_count": {
                    "$size": {
                        "$filter": {
                            "input": {"$ifNull": ["$segments", []]},
                            "as": "s",
                            "cond": {"$eq": ["$$s.annotations.eating", True]},
                        }
                    }
                },
            }
        },
    ]

    # Remove empty match stage if not needed
    pipeline = [stage for stage in pipeline if stage]

    db = get_db(Data.Deakin)
    segments_collection = db["segments"]
    results = list(segments_collection.aggregate(pipeline))

    return {
        result["date"]: (result["segment_count"], result["eating_count"])
        for result in results
    }


def get_image_counts_per_date(patient_id: str | None = None) -> dict[str, int]:
    match_stage = {}
    if patient_id:
        match_stage["patient.id"] = patient_id

    pipeline = [
        {"$match": match_stage} if match_stage else {},
        {"$group": {"_id": "$date", "image_count": {"$sum": 1}}},
    ]

    pipeline = [stage for stage in pipeline if stage]

    db = get_db(Data.Deakin)
    results = list(image_collection(db).aggregate(pipeline))
    return {result["_id"]: result["image_count"] for result in results}
