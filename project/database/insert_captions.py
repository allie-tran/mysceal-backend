# small_episode,event_id,main_image,ImageID,Time,medium_episode_id,big_episode_id,long_description
# 87,75002,/home/ltran/spinning-storage/ltran/blip2_embedding/201909/04/20190904_145250_000.npy,20190904_145250_000,2019-09-04 14:52:50,3191,60,"I see a blurry image of a room with several people walking around. There are two people standing near the center of the room, while another person is standing on the right side of the room. The room is decorated with blue walls and ceilings, as well as a number of light fixtures hanging from the ceiling. I also see a number of chairs scattered around the room, providing a comfortable space for people to sit and socialize."

import pandas as pd
from pymongo import MongoClient

client = MongoClient("localhost", 27017)
db = client["LSC24_new"]

caption_file = "~/data_mysceal/LSC23/df_small_epispde_long_description.csv"
df = pd.read_csv(caption_file)

# Make text index for caption, address, location, and ocr
# drop all text indexes
db["images"].drop_index("captions_text")
db["images"].create_index([
    ("caption", "text"),
    ("address", "text"),
    ("location", "text"),
], default_language="english", weights={ "caption": 10, "address": 1, "location": 1 })

# # convert main_image to image_id
# df["main_image"] = df["main_image"].apply(lambda x: x.replace("/home/ltran/spinning-storage/ltran/blip2_embedding/", ""))
# df["main_image"] = df["main_image"].apply(lambda x: x.replace(".npy", ".jpg"))

# # insert caption into images collection
# print("Inserting captions into images collection")
# for index, row in tqdm(df.iterrows(), total=len(df)):
#     image = row["main_image"]
#     caption = row["long_description"]
#     db["images"].update_one({"image": image}, {"$set": {"caption": caption}})








