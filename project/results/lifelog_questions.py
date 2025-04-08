import os
import cv2
from PIL import Image
from query_parse.types.requests import Data


def create_video(data: Data, images: list[str]):
    if data == Data.LSC23:
        IMAGE_DIR = "/home/allie/data_mysceal/Images/LSC23/"
    elif data == Data.Deakin:
        IMAGE_DIR = "/home/allie/data_mysceal/Images/Deakin/"

    # get the images
    images = [os.path.join(IMAGE_DIR, img) for img in images]
    # get the image size
    img = Image.open(images[0])
    width, height = img.size
    # create a video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_file_path = "temp.mp4"
    video = cv2.VideoWriter(video_file_path, fourcc, 5, (width, height))

    for img in images:
        image = cv2.imread(img)
        if image is None:
            print(f"Error reading image {img}")
            continue
        video.write(image)

    cv2.destroyAllWindows()
    video.release()

    # remove the video file
    # os.remove(video_file_path)
    return video_file_path
