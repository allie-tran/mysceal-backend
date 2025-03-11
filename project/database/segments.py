from typing import List
import numpy as np
from sklearn.cluster import DBSCAN

from llm import vllm_model
from llm.models import MixedContent
from myeachtra.dependencies import CamelCaseModel
from query_parse.types.requests import Data
from query_parse.visual import get_model
from question_answering.video import get_openai_visual_message
from results.models import Image
from rich import print as rprint

from database.main import get_db
from retrieval.dynamic_segmentation import get_low_visual_density_indices


# ====================== #
# SEGMENTS
# ====================== #
class Annotation(CamelCaseModel):
    eating: bool = False

    # config so that it accept any key
    class Config(CamelCaseModel.Config):
        extra = "allow"


class EventSegment(CamelCaseModel):
    images: List[Image] = []
    keyframes: List[Image] = []
    annotations: Annotation


class EventSegments(CamelCaseModel):
    date: str
    patient_id: str
    segments: List[EventSegment] = []
    count: int = 0
    manually_checked: bool = False


def save_segments_to_db(data: Data, segments: EventSegments, skip_merge: bool = False):
    """
    Save segments to the database
    """
    db = get_db(data)
    # Merge consecutive segments with the same annotations
    if not skip_merge:
        segments = merge_segments(segments)

    # update keyframes
    for segment in segments.segments:
        if not segment.keyframes:
            segment.keyframes = get_keyframes_from_segments(data, segment.images)

    upserted = db["segments"].update_one(
        {
            "patient_id": segments.patient_id,
            "date": segments.date,
        },
        {"$set": segments.model_dump()},
        upsert=True,
    )
    if upserted:
        print(f"Segments saved for {segments.patient_id} on {segments.date}")
    else:
        raise Exception(
            f"Failed to save segments for {segments.patient_id} on {segments.date}"
        )


def get_saved_segments(data: Data, patient_id: str, date: str) -> EventSegments | None:
    """
    Get segments from the database
    """
    db = get_db(data)
    segments = db["segments"].find_one(
        {
            "patient_id": patient_id,
            "date": date,
        }
    )
    if segments:
        return EventSegments.model_validate(segments)


def merge_segments(segments: EventSegments) -> EventSegments:
    """
    Merge consecutive segments with the same annotations
    """
    merged_segments = []
    current_segment = None
    for segment in segments.segments:
        if not current_segment:
            current_segment = segment
        elif segment.annotations.eating == current_segment.annotations.eating:
            current_segment.images += segment.images
        else:
            merged_segments.append(current_segment)
            current_segment = segment
    if current_segment:
        merged_segments.append(current_segment)

    segments.segments = merged_segments
    return segments

def get_keyframes_from_segments(data: Data, images: List[Image]) -> List[Image]:
    # for each segment, use dbscan to cluster the images
    # for each cluster, get the average score
    # for each cluster, get the image with the closest score to the average score and the highest to others average scores
    # return the list of images
    model = get_model(data)
    photo_ids = model.photo_ids[data]
    features = model.norm_photo_features[data]
    encoded_query = model.encode_text("I am eating or interacting with food")
    low_density_indices = get_low_visual_density_indices(data)

    if len(images) < 4:
        return images

    image_src_to_image = {image.src: image for image in images}
    image_srcs = [image.src for image in images]
    image_set = set(image_srcs)

    # Get the segment images that are not in the low density indices
    segment_ids = [i for i, image in enumerate(photo_ids) if image in image_set]
    segment_ids = [i for i in segment_ids if i not in low_density_indices]
    good_images = [image_src_to_image[photo_ids[i]] for i in segment_ids]

    if len(good_images) < 4:
        return good_images

    segment_features = features[np.array(segment_ids)]

    # cluster the images
    dbscan = DBSCAN(eps=0.03, min_samples=2, metric="cosine")
    clusters = dbscan.fit_predict(segment_features)

    chunk = []
    for cluster in set(clusters):
        cluster_images = [image for i, image in enumerate(good_images) if clusters[i] == cluster]
        cluster_set = set([image.src for image in cluster_images])
        if len(cluster_images) == 1:
            chunk.append(cluster_images[0])
        else:
            cluster_ids = [i for i, image in enumerate(photo_ids) if image in cluster_set]
            cluster_features = features[np.array(cluster_ids)]
            cluster_feat = np.mean(cluster_features, axis=0)
            cluster_feat = cluster_feat / np.linalg.norm(cluster_feat)

            distinct_scores = cluster_features @ cluster_feat.T
            image_scores = cluster_features @ encoded_query.T
            image_scores = image_scores + distinct_scores
            closest_image = cluster_images[np.argmax(image_scores)]
            chunk.append(closest_image)

    # sort the images by the order they appear in the segment
    chunk = sorted(chunk, key=lambda x: image_srcs.index(x.src))
    return chunk

async def annotate_segments_vllm(
    segments: List[EventSegment], data: Data
) -> List[EventSegment]:
    # Get the list of images
    for i, segment in enumerate(segments):
        if not segment.annotations.eating:
            continue
        content = [
            MixedContent(
                type="text",
                content="""Here are some first person images of a person for a period of time. Please annotate the images to indicate when the person is eating with the following annotation:

Location Setting:
- Green Space: A park, garden, or other green space.
- Home: Inside a house or apartment.
- Workplace: Inside an office or other workplace.
- University/School: Inside a university or other educational institution.
- Food Venue: Inside a restaurant, cafe, or other food venue.
- Sporting Venue: Inside a sports stadium or other sporting venue.
- Out of Home: Other public or outdoor location outside of the above categories.

Location Position:
- Sitting at a table: Sitting at a table or desk.
- Sitting on a chair: Sitting on a chair or other seat.
- Sitting on the couch: Sitting on a couch or sofa.
- Standing/Walking: Standing or walking.

Mood:
- Positive: Happy, excited, or other positive emotions.
- Neutral: Neutral or calm emotions.
- Negative: Sad, angry, or other negative emotions.

Food categories: food (or drink) in the image:
- Fruit: A piece of fruit or a fruit bowl.
- Vegetable: A plate of vegetables or a salad.
- Grain: A sandwich, pasta, or other grain-based food.
- Protein: A piece of meat, fish, or other protein.
- Dairy: A glass of milk, cheese, or other dairy product.
- Unhealthy: A piece of cake, candy, or other unhealthy food.
- Alcohol: A glass of wine, beer, or other alcoholic beverage.

Social Setting:
- Alone: No other people in the image.
- Person(s) Present: One or more people in the image
- Interating with person(s): One or more people in the image, and the person is interacting with them.
- Social event or gathering: A party, meeting, or other social event.

Eating Activity:
- Using a handheld device (phone, tablet)
- Using a screen for work/recreation (computer, console)
- Watching TV or a film
- In transit (car, bus, train)
- Other recreational activity (reading, listening to music, playing a board game)

Leave the annotation blank if it is not possible to determine the annotation from the image.

```json
{{
    "Location Setting": "Home",
    "Location Position": "Sitting at a table",
    "Mood": "Positive",
    "Food Category": ["Fruit", "Vegetable"], # list of food items
    "Food": "Watermelon, salad, hamburger, fries, coke", # the actual food items
    "Social Setting": "Person(s) Present",
    "Eating Activity": "Watching TV or a film",
    "captions": " a objective description of the image, in a style similar to a food log entry for medical records"
}}
```
""",
            )
        ]
        images = get_keyframes_from_segments(data, segment.images)
        # split the images into smaller chunks (max 9 images per chunk)
        max_images_per_chunk = 4
        for j in range(0, len(images), max_images_per_chunk):
            chunk = images[j : j + max_images_per_chunk]
            message = get_openai_visual_message(chunk, data=data)
            if message:
                content.append(message)

        if len(content) > 1:
            task = vllm_model.generate_from_mixed_media(content)
            async for llm_response in task:
                try:
                    segments[i].annotations = Annotation.model_validate(llm_response)
                    segments[i].annotations.eating = True
                    rprint(segments[i].annotations)
                except Exception as e:
                    rprint(e)
                    rprint("GPT", llm_response)
    return segments
