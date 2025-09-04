import glob
import os
from tqdm import tqdm
# /mnt/ssd0/Images/Deakin/ID100/2021/12/06/

DATA_DIR = "/mnt/ssd0/Images/Deakin/"

images = glob.glob(DATA_DIR + "**/._*.jpg", recursive=True)
# remove images that starts with "."
print(f"Found {len(images)} images that match the pattern.")

print("First 10 images:")
for img in images[:10]:
    print(img)

# Remove
for img in tqdm(images):
    os.remove(img)  # Uncomment this line to actually remove the files





