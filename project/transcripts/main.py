from datetime import datetime, timedelta
import json
import os
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
import faiss
from tqdm import tqdm
from llm import llm_model
from query_parse.types.requests import Data
from visual.segments import presegments

client = MongoClient("mongodb://localhost:27017")
db = client["castle"]
transcripts = list(db.transcripts.find({}, {"_id": 0, "person": 1, "start": 1, "end": 1, "text": 1, "day": 1}))

# Group by person and sort by time
from collections import defaultdict

by_person = defaultdict(list)
for t in transcripts:
    by_person[t["person"]].append(t)

# Embed and index
model = SentenceTransformer("all-MiniLM-L6-v2")

def find_transcript(day: str, person: str | None, start: datetime, end: datetime, return_dict:bool = False):
    """
    Find the transcript for a given day, person, start and end time.
    """
    if not person:
        return ""
    time_at_zero = datetime(start.year, start.month, start.day, 0, 0, 0).astimezone(start.tzinfo)
    query = {
        "day": f"day{int(day)}",
        "person": person,
        "end": {"$gte": (start - time_at_zero).total_seconds()},
        "start": {"$lte": (end - time_at_zero).total_seconds()}
    }
    results = db.transcripts.find(query, {"text": 1, "start": 1}).sort("start", 1)
    t =  " ".join([r["text"] for r in results])
    if return_dict:
        return {
            "day": f"day{int(day)}",
            "person": person,
            "start": (start - time_at_zero).total_seconds(),
            "end": (end - time_at_zero).total_seconds(),
            "text": f"[{day}][Camera: {person}] {t.strip()}"
        }
    return t

def format_transcript(doc: dict) -> str:
    """
    Format the transcript document for display.
    """
    start_time = datetime(2023, 1, 1, 0, 0) + timedelta(seconds=doc['start'])
    end_time = datetime(2023, 1, 1, 0, 0) + timedelta(seconds=doc['end'])
    return f"[{doc['day']}][Camera: {doc['person']}][{start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}] {doc['text']}"

OVERWRITE = False
if not OVERWRITE and os.path.exists("event_transcripts.json"):
    with open("event_transcripts.json", "r") as f:
        docs = json.load(f)
    print("Loaded", len(docs), "transcripts from docs.json.")
else:
    events = presegments[Data.CASTLE].events
    docs: list[dict] = []
    print("Finding transcripts for", len(events), "events...")
    for event in tqdm(events):
        docs.append(find_transcript(  # type: ignore
            event.start_time.strftime("%d"),
            event.user_id,
            event.start_time,
            event.end_time,
            return_dict=True
        ))
    print("Found", len(docs), "transcripts.")
    with open("event_transcripts.json", "w") as f:
        json.dump(docs, f, indent=2)

EVENT_WINDOW = 10 # group 5 events
EVENT_SLIDE = 5

event_docs = []
for i in range(0, len(docs), EVENT_SLIDE):
    if i + EVENT_WINDOW > len(docs):
        break
    event_docs.append({
        "text": "\n".join(format_transcript(doc) for doc in docs[i:i + EVENT_WINDOW]),
        "start": docs[i]["start"],
        "end": docs[i + EVENT_WINDOW - 1]["end"],
        "day": docs[i]["day"],
        "person": docs[i]["person"]
    })

print("Found", len(event_docs), "event documents.")

if not OVERWRITE and os.path.exists("event_transcripts_index.faiss"):
    index = faiss.read_index("event_transcripts_index.faiss")
    print("Loaded index with", index.ntotal, "documents.")
else:
    print("Building index...")
    embeddings = model.encode([doc['text'] for doc in event_docs])
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)  # type: ignore
    print("Index built with", len(docs), "documents.")
    faiss.write_index(index, "event_transcripts_index.faiss")

def get_answer_from_transcript(data: Data, query: str, top_k: int=20):
    q_vec = model.encode([query])
    _, I = index.search(q_vec, top_k)  # type: ignore

    retrieved = [event_docs[i] for i in I[0]]
    context = "\n".join(format_transcript(doc) for doc in retrieved)
    print("Retrieved", len(retrieved), "documents for query:", query)
    prompt = f"""Transcripts:\n{context}\n\nQuestion: {query}\nAnswer:
    If it is not possible to answer the question, reply with an empty string.
    Else, provide a JSON object with the following format:
    ```json
    {{
        "answer": "your answer here"
        "explanation": "brief explanation for your answer, with quotes of the relevant parts of the transcript (from which camera, day, and time) if possible",
    }}
    ```
    """
    return llm_model.generate_from_text(data, prompt)
