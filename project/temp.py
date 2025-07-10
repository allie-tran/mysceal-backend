from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

client = MongoClient("mongodb://localhost:27017")
db = client["castle"]
collection = db["images"]

BATCH_SIZE = 1000
cursor = collection.find({"img": {"$exists": True}}, {"_id": 1, "img": 1})
total = collection.count_documents({"img": {"$exists": True}})

bulk_ops = []
count = 0

print("Renaming 'img' → 'image'...")

for doc in tqdm(cursor, total=total):
    bulk_ops.append(UpdateOne(
        {"_id": doc["_id"]},
        {
            "$set": {"image": doc["img"]},
            "$unset": {"img": ""}
        }
    ))

    if len(bulk_ops) == BATCH_SIZE:
        collection.bulk_write(bulk_ops, ordered=False)
        bulk_ops = []

if bulk_ops:
    collection.bulk_write(bulk_ops, ordered=False)

print(f"✅ Renamed 'img' to 'image' in {total} documents.")
