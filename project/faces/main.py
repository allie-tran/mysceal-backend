from database.main import get_db, image_collection
from PIL import Image, ImageDraw
from query_parse.types.requests import Data

def draw_bounding_boxes(data: Data, image_paths: list[str]):
    """
    Draw bounding boxes on the image based on the provided data.

    Args:
        data (Data): The data containing bounding box information.
        image (str): The path to the image file.
    """
    images_data = image_collection(get_db(data)).find(
        {"image": {"$in": image_paths}},
        {"_id": 0, "image": 1, "faces": 1}
    )
    image_objs = []
    for path in image_paths:
        try:
            image_objs.append(Image.open(path))
        except Exception:
            print("Error opening image", path)
            continue
    if len(image_objs) == 0:
        return []

    for img_data in images_data:
        index = image_paths.index(img_data["image"])
        img = image_objs[index]
        for face in img_data.get("faces", []):
            name = face.get("name", "")
            bbox = face.get("bbox", [])
            color = face.get("color", "red")
            if len(bbox) == 4:
                draw = ImageDraw.Draw(img)
                draw.rectangle(bbox, outline=color, width=2)
                if name:
                    draw.text((bbox[0], bbox[1]), name, fill=color)
        image_objs[index] = img
    return image_objs
