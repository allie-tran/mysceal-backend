import json
import logging
from contextlib import asynccontextmanager
from io import BytesIO
import os
from typing import List, Optional
from uuid import uuid4

import pandas as pd
import redis
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from rich import print

from configs import DEV_MODE, REDIS_HOST, REDIS_PORT
from database.encode_blurhash import batch_encode
from database.segments import (
    Annotation,
    EventSegment,
    EventSegments,
    annotate_segments_vllm,
    get_saved_segments,
    save_segments_to_db,
)
from database.utils import get_full_data, get_image_counts_per_date, get_segment_counts_per_date, get_unique_patient_ids, get_unique_values
from myeachtra.auth_models import get_user, verify_user
from myeachtra.map_router import map_router
from myeachtra.timeline_router import timeline_router
from query_parse.types.lifelog import EatingFilters
from query_parse.types.requests import (
    AnswerThisRequest,
    ChoicesRequest,
    ChoicesResponse,
    Data,
    EditAnnotationRequest,
    ExpandSegmentRequest,
    GeneralQueryRequest,
    ImageInfoRequest,
    LoginRequest,
    LoginResponse,
    SegmentRequest,
    SimilaritySearchRequest,
)
from results.lifelog_questions import create_video
from results.models import AnswerResultWithEvent, EventResults, TripletEventResults
from retrieval.dynamic_segmentation import (
    expand_single_image,
    get_keyframes_from_segments,
)
from retrieval.graph import get_vegalite, to_csv
from retrieval.search import answer_single_event, get_segments_only, search_similar_events, streaming_manager
from submit.router import submit_router
from visual.main import get_model

logging.basicConfig(level=logging.DEBUG)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
load_dotenv(".env")


@asynccontextmanager
async def start_up(_: FastAPI):
    # async for __ in single_query("I was walking on snow outside of Ireland", EatingFilters(), Data.LSC23):
    #     continue
    # get_segments_only(
    #     "I am eating, or preparing food, or food is visible",
    #     EatingFilters(patient_id=["ID193"], date=["2022/08/14"]),
    #     data=Data.Deakin,
    # )
    print("App ready")
    yield


app = FastAPI(lifespan=start_up)
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "https://n-2mbzycnxd-allie-trans-projects.vercel.app",
    "https://mysceal.computing.dcu.ie",
    "vercel.app",
    "mysceal.computing.dcu.ie",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
# app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(submit_router, prefix="/submit")
app.include_router(timeline_router, prefix="/timeline")
app.include_router(map_router, prefix="/location")


@app.post("/login", description="Login endpoint", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint
    """
    print("Logging", request.username, "in")
    return verify_user(request)


@app.post(
    "/search",
    description="Send a search request. Returns a token to be used to stream the results",
    dependencies=[Depends(get_user)],
)
async def search(request: GeneralQueryRequest):
    # Save to redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    token = uuid4().hex
    message = request.model_dump_json()
    r.set(token, message)
    print("Got search request!")
    return {"searchToken": token}


@app.get(
    "/get-stream-results/{session_id}/{token}",
    description="Stream the search results",
    status_code=200,
)
async def get_stream_results(session_id: str, token: str):
    if not session_id and not DEV_MODE:
        raise HTTPException(status_code=401, detail="Please log in")

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    message = r.get(token)

    # Delete the message from redis after getting it
    r.delete(token)

    if not message:
        raise HTTPException(status_code=404, detail="Token not found")

    print("Starting search")
    request_body = json.loads(message.decode("utf-8"))  # type: ignore
    request = GeneralQueryRequest(**request_body)

    return StreamingResponse(streaming_manager(request), media_type="text/event-stream")


@app.get(
    "/encode-blurhash",
    description="Encode images",
    status_code=200,
)
async def encode():
    """
    Encode images using blurhash so that they can be displayed
    in place of the actual image when loading
    """
    batch_encode()
    return {"message": "ok"}


@app.post(
    "/answer-this",
    description="Answer a question on a scene",
    status_code=200,
    response_model=List[AnswerResultWithEvent],
)
async def answer_this(request: AnswerThisRequest):
    """
    Answer a question on a scene
    """
    answers = []
    async for answer in answer_single_event(request):
        answers.append(answer)
    return answers

@app.post(
    "/similarity-search",
    description="Search for similar images",
    status_code=200,
    response_model=Optional[TripletEventResults],
)
async def similarity_search(request: SimilaritySearchRequest):
    """
    Search for similar images based on a query
    """
    return await search_similar_events(
        request.image,
        request.data
    )


@app.post(
    "/query_to_csv",
    description="Given a query, return the results in CSV format",
    status_code=200,
    response_model=str,
)
async def query_to_csv(query: GeneralQueryRequest):
    """
    Given a query, return the results in CSV format
    """
    csv = await to_csv(query.main, query.data)
    return csv.to_csv(index=False)


@app.get("/health", description="Health check endpoint", status_code=200)
async def health():
    """
    Health check endpoint
    """
    return {"status": "ok"}


@app.post(
    "/query_to_vegalite",
    description="Given a query, return the results in Vega-Lite format",
    status_code=200,
    response_model=dict,
)
async def query_to_vegalite(query: GeneralQueryRequest):
    """
    Given a query, return the results in Vega-Lite format
    """
    data = await get_vegalite(query.main, query.data)
    return data


@app.post(
    "/image-dicts",
    description="Get all information about the images in the database",
    status_code=200,
)
async def get_image_dicts(request: ImageInfoRequest):
    """
    Get all information about the images in the database
    """
    return get_full_data(request.images, request.data)


@app.post(
    "/choices",
    description="Get the choices for a dropdown",
    status_code=200,
    response_model=ChoicesResponse,
)
async def get_choices(request: ChoicesRequest):
    """
    Get the choices for a dropdown
    """
    match (request.data, request.field):
        case Data.Deakin, "patientId":
            return get_unique_patient_ids()
        case _, "date":
            choices = get_unique_values(request.data, "date", request.condition)
            annotations = []
            if request.condition and "patient.id" in request.condition:
                patient_id = request.condition.get("patient.id", "")
                image_counts = get_image_counts_per_date(patient_id)
                segment_counts = get_segment_counts_per_date(patient_id)
                print("Segment counts", segment_counts)
                for date in choices:
                    if date in segment_counts:
                        length, eating = segment_counts[date]
                        annotations.append(f"{date} ({length} segments, {eating} eating)")
                    else:
                        img_count = image_counts.get(date, 0)
                        annotations.append(f"{date} ({img_count} images)")
            return ChoicesResponse(choices=choices, annotations=annotations)
        case _:
            raise HTTPException(
                status_code=404, detail=f"{request.field} not found for {request.data}"
            )


@app.post(
    "/segments",
    description="Get all segments",
    status_code=200,
    response_model=EventSegments,
)
async def get_segments(request: SegmentRequest):
    """
    Get all segments for a patient in a given date
    """
    segments = []
    if request.use_cache:
        saved_segments = get_saved_segments(
            request.data, request.patient_id, request.date
        )
        if saved_segments:
            count = sum([len(segment.images) for segment in saved_segments.segments])
            saved_segments.count = count
            return saved_segments

    query = "I am eating, or preparing food, or food (or drink) is visible"
    events, num, eating, heatmap = get_segments_only(
        query,
        EatingFilters(patient_id=[request.patient_id], date=[request.date]),
        data=request.data,
    )
    encoded_query = get_model(Data.Deakin).encode_text(query)

    for i, event in enumerate(events):
        segments.append(
            EventSegment(
                images=event.images,  # type: ignore
                annotations=Annotation(
                    eating=eating[i],
                ),
                keyframes=get_keyframes_from_segments(
                    encoded_query, request.data, event.images
                ),
            )
        )

    results = EventSegments(
        patient_id=request.patient_id,
        date=request.date,
        segments=segments,
        count=num,
        heatmap=heatmap,
    )
    save_segments_to_db(request.data, results, skip_merge=True)
    return results


@app.post(
    "/toggle-eating",
    description="Toogle eating",
    status_code=200,
)
async def toogle_eating(request: ExpandSegmentRequest):
    """
    Toggle eating
    """
    segments = get_saved_segments(request.data, request.patient_id, request.date)
    if not segments:
        print("Segments not found")
        raise HTTPException(
            status_code=404,
            detail=f"Segments not found for {request.patient_id} on {request.date}",
        )

    # find the image_obj
    segment_idx = -1
    new_start = None
    new_end = None
    is_eating = False
    print("Request", request.image)
    for i, segment in enumerate(segments.segments):
        images = [img.src for img in segment.images]
        start_image = images[0]
        end_image = images[-1]

        if request.image in images:
            is_eating = segment.annotations.eating
            print("Found image in segment", i, "eating", is_eating)
            print("Index", images.index(request.image))

            if len(segment.images) == 1:
                print("Single image segment")
                new_annotations = segment.annotations
                new_annotations.eating = not is_eating
                new_segments = segments.segments[:i]
                new_segments.append(
                    EventSegment(
                        images=segment.images,
                        annotations=new_annotations,
                    )
                )
                new_segments += segments.segments[i + 1 :]
                save_segments_to_db(
                    request.data,
                    EventSegments(
                        patient_id=request.patient_id,
                        date=request.date,
                        segments=new_segments,
                        manually_checked=True
                    ),
                )
                return segments.segments

            query = (
                "I am eating or interacting with food"
                if not is_eating
                else "I am not eating"
            )
            new_start, new_end = expand_single_image(
                request.data,
                query,
                request.image,
                start_image,
                end_image,
            )
            segment_idx = i
            break

    # update the segment
    if new_start and new_end:
        new_segments = segments.segments[:segment_idx]
        # split the segment into 3
        segment = segments.segments[segment_idx]
        images = [img.src for img in segment.images]
        print(
            "Checking image in segment", segment_idx, "at", images.index(request.image)
        )
        image_idx = images.index(request.image)
        new_start_idx = images.index(new_start)
        new_end_idx = images.index(new_end)
        new_label = not is_eating
        count = 0
        first_images = segment.images[:new_start_idx]
        if first_images:
            count += 1
            new_segments.append(
                EventSegment(
                    images=first_images,
                    annotations=Annotation(
                        eating=new_label if image_idx < new_start_idx else is_eating,
                    ),
                )
            )

        second_images = segment.images[new_start_idx:new_end_idx]
        if second_images:
            count += 1
            new_segments.append(
                EventSegment(
                    images=second_images,
                    annotations=Annotation(
                        eating=(
                            new_label
                            if image_idx >= new_start_idx and image_idx < new_end_idx
                            else is_eating
                        ),
                    ),
                )
            )

        third_images = segment.images[new_end_idx:]
        if third_images:
            count += 1
            new_segments.append(
                EventSegment(
                    images=third_images,
                    annotations=Annotation(
                        eating=new_label if image_idx >= new_end_idx else is_eating,
                    ),
                )
            )

        print("Split into", count, "segments")
        print("Request image", request.image, "found at", images.index(request.image))
        print(
            (0, new_start_idx),
            (new_start_idx, new_end_idx),
            (new_end_idx, len(segment.images)),
        )

        new_segments += segments.segments[segment_idx + 1 :]

        save_segments_to_db(
            request.data,
            EventSegments(
                patient_id=request.patient_id, date=request.date, segments=new_segments,
                manually_checked=True,  # Set to True to indicate manual changes

            ),
        )
        return new_segments

    print("Image not found in segments")
    raise HTTPException(
        status_code=404,
        detail=f"Image {request.image} not found in the segments",
    )


@app.post(
    "/toggle-eating-all",
    description="Toogle eating for all images in a segment",
    status_code=200,
)
async def toogle_eating_all(request: ExpandSegmentRequest):
    """
    Toggle eating for all images in a segment
    """
    segments = get_saved_segments(request.data, request.patient_id, request.date)
    if not segments:
        print("Segments not found")
        raise HTTPException(
            status_code=404,
            detail=f"Segments not found for {request.patient_id} on {request.date}",
        )

    is_eating = False
    print("Request", request.image)
    for i, segment in enumerate(segments.segments):
        images = [img.src for img in segment.images]

        if request.image in images:
            is_eating = segment.annotations.eating
            print("Found image in segment", i, "eating", is_eating)
            print("Index", images.index(request.image))

            new_segments = segments.segments[:i]
            new_segments.append(
                EventSegment(
                    images=segment.images,
                    annotations=Annotation(
                        eating=not is_eating,
                    ),
                )
            )
            new_segments += segments.segments[i + 1 :]
            save_segments_to_db(
                request.data,
                EventSegments(
                    patient_id=request.patient_id,
                    date=request.date,
                    segments=new_segments,
                    manually_checked=True,
                ),
            )
            return segments.segments

    print("Image not found in segments")


@app.post("/annotate-segments", description="Annotate segments", status_code=200)
async def annotate_segments(request: SegmentRequest):
    """
    Annotate segments
    """
    event_segments = get_saved_segments(request.data, request.patient_id, request.date)
    if not event_segments:
        raise HTTPException(
            status_code=404,
            detail=f"Segments not found for {request.patient_id} on {request.date}",
        )

    segments = await annotate_segments_vllm(event_segments.segments, request.data)
    save_segments_to_db(
        request.data,
        EventSegments(
            patient_id=request.patient_id, date=request.date, segments=segments,
        ),
        skip_merge=True,
    )
    return segments

@app.post("/edit-annotations", description="Edit annotations", status_code=200)
async def edit_annotations(request: EditAnnotationRequest):
    """
    Edit annotations for a segment
    """
    segments = get_saved_segments(request.data, request.patient_id, request.date)
    if not segments:
        raise HTTPException(
            status_code=404,
            detail=f"Segments not found for {request.patient_id} on {request.date}",
        )

    # Find the segment by ID
    segment_id = request.segment_id
    for i, segment in enumerate(segments.segments):
        if i == segment_id:
            # Update the annotation field
            annotations = segment.annotations.model_dump()
            for key, value in request.annotations.items():
                if key in annotations:
                    annotations[key] = value
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Annotation field {key} not found in segment",
                    )
            segments.segments[i] = EventSegment(
                images=segment.images,
                annotations=Annotation(**annotations),
                keyframes=segment.keyframes,
            )
            print(f"Updated segment {segment_id} annotations: {annotations}")
            break
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Segment with ID {segment_id} not found",
        )

    segments.manually_checked = True
    save_segments_to_db(request.data, segments, skip_merge=True)
    return segments

@app.post("/download-segments", description="Download segments", status_code=200)
async def download_segments(request: SegmentRequest):
    """
    Download segments
    """
    event_segments = get_saved_segments(request.data, request.patient_id, request.date)
    if not event_segments:
        raise HTTPException(
            status_code=404,
            detail=f"Segments not found for {request.patient_id} on {request.date}",
        )

    fields = set()
    for segment in event_segments.segments:
        fields.update(segment.annotations.model_dump().keys())
    # Write it into a CSV file with the following columns:
    # Patient ID, Date, Image, Eating, Segment ID, [all other fields]
    data = []
    for i, segment in enumerate(event_segments.segments):
        for image in segment.images:
            row = {
                "Patient ID": request.patient_id,
                "Date": request.date,
                "Image": image.src,
                "Segment ID": f"{request.patient_id}_{request.date}_{i:03d}",
                "Eating": segment.annotations.eating,
            }
            row.update(segment.annotations.model_dump())
            row = {to_title_case(k): v for k, v in row.items()}
            data.append(row)

    # Write to CSV
    file = BytesIO()
    df = pd.DataFrame(data)
    df.to_csv(file, index=False)
    file.seek(0)
    return StreamingResponse(
        file,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=segments.csv"},
    )

@app.post("/export-to-video",
    description="Export segments to video",
    status_code=200)
async def export_to_video(request: List[str]):
    """
    Export segments to video
    """
    video_path = create_video(Data.LSC23, request)

    def iterfile():
        with open(video_path, mode="rb") as file:
            yield from file

    file_size = os.path.getsize(video_path)

    headers = {
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes"
    }

    return StreamingResponse(iterfile(), headers=headers, media_type="video/mp4")

def to_title_case(string: str) -> str:
    return " ".join([word.capitalize() for word in string.split("_")])
