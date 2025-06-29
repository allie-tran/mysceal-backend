import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone as pytz_timezone
from pymongo import MongoClient
from tqdm import tqdm

vaisl_gps = "~/data_mysceal/LSC23/vaisl_gps.csv"
vaisl_gps = pd.read_csv(vaisl_gps)

client = MongoClient("mongodb://localhost:27017/")
db = client["LSC24_new"]
collection = db["images"]

# Step 1: Aggregate duplicate _ids (keep one, delete the rest)
pipeline = [
    {"$group": {
        "_id": "$minute_id",
        "ids": {"$push": "$_id"},
        "count": {"$sum": 1}
    }},
    {"$match": {"count": {"$gt": 1}}},
    {"$project": {
        "_id": 0,
        # take all but the first _id in the list
        "ids": {"$slice": ["$ids", 1, {"$size": "$ids"}]}
    }}
]

to_delete = collection.aggregate(pipeline)
ids_to_delete = [doc_id for group in to_delete for doc_id in group["ids"]]

# Step 2: Delete all extra documents in a single operation (chunked if needed)
batch_size = 1000
for i in tqdm(range(0, len(ids_to_delete), batch_size), desc="Removing duplicates"):
    batch = ids_to_delete[i:i+batch_size]
    collection.delete_many({"_id": {"$in": batch}})

# Create a new index on minute_id to ensure uniqueness
collection.create_index("minute_id", unique=True)

to_changes = {}
for i, row in tqdm(vaisl_gps.iterrows(), total=len(vaisl_gps)):
    timezone = row["new_timezone"]
    minute_id = row["minute_id"] #20190101_1037
    # convert to str
    minute_id = str(minute_id)
    timezone = str(timezone)
    if timezone == "nan":
        continue

    utc_time = datetime.strptime(minute_id, "%Y%m%d_%H%M")
    utc_time = utc_time.replace(tzinfo=pytz_timezone("UTC"))
    local_tz = pytz_timezone(timezone)

    # calculate local time
    local_time = utc_time.astimezone(local_tz)

    # check if different from utc_time
    # convert to string
    utc_time_str = utc_time.strftime("%Y-%m-%d %H:%M:%S%z")
    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S%z")
    if utc_time_str != local_time_str:
        to_changes[minute_id] = (minute_id, local_time_str, local_time, timezone)

# Loop through the mongo
# database and update the time and timezone fields
pbar = tqdm(total=len(to_changes), desc="Updating database")
for minute_id, (minute_id, local_time_str, local_time, timezone) in to_changes.items():
    pbar.update(1)
    pbar.set_postfix(minute_id=minute_id, local_time=local_time_str, timezone=timezone)
    collection.update_many(
        {"minute_id": minute_id},
        {"$set": {"time": local_time, "timezone": timezone, "local_time": local_time_str}}
    )





