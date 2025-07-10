import datetime
import pickle
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from llm import llm_model
from retrieval.scripts import (
    TIME_BUCKETS,
    TIME_TO_IDX,
    TOTAL_DAYS,
    date_str_to_doy,
    generate_matrix_from_function_multi_years,
)
from rich import print
from tqdm import tqdm

from visual.types import Array1D, Array2D

# %%
with open("retrieval/scripts.py") as f:
    script = f.read()

# %%
heatmap_prompt = """
You are a temporal reasoning assistant.
Given a natural language phrase that refers to a point or period in time, return a 2D heatmap matrix that represents the probability distribution of this phrase over a calendar year.


The matrix should have:
	•	365 columns, each representing one day of the year (day 0 = Jan 1, day 364 = Dec 31)
	•	4 rows for times of day: "Morning", "Afternoon", "Evening", "Night"

Each cell (row i, col j) should contain a float between 0 and 1 representing the likelihood that the phrase refers to that time on that day.
The sum of all values in the matrix does not equal 1. Each cell is independent.

Phrase: {phrase}

If no specific date is mentioned or inferred, return a JSON object with the following format:

```json
None
```

If no specific time is mentioned, omit the "time" fields.

Else, return a JSON object with the following format:
```json
{{
  "time_buckets": ["Morning", "Afternoon", "Evening", "Night"],
  "entries": [ # a sparse matrix, no truncate
    {{"date": "24-12", "time": "Morning", "probability": 1}},
    {{"date": "24-12", "time": "Afternoon", "probability": 0.5}},
    {{"date": "25-12", "time": "Morning", "probability": 1}},
    ...
  ]
}}
```

If there are too many entries or it is better to generate the matrix algorithmaticaly, return a JSON object describing a function for generating a temporal heatmap.

The JSON should include:
- "time_buckets": list of 4 standard time-of-day labels
- "functions": a list of object describing when and where the values apply
In each function object, include the year if applicable (2019, 2020, or both)

Return one of the following function types:
- "weekends_only": applies on Saturdays and Sundays
- "weekdays_only": applies on Monday–Friday
- "month_range": applies from start "MM-YYYY" to end "MM-YYYY" (e.g. "01" to "12")
- "day_range": applies from start_day to end_day (MM-DD format, e.g. "01-01" to "12-31")
- "specific_dates": applies on specific "DD-MM" dates
- "daily_pattern": applies the same value every day at specified times
- "weekday_pattern": applies to specific weekday names (e.g. Monday, Friday)
- "intersection": applies all conditions and multiplies with "value" (conditions are sub-functions)
- "union": applies all conditions and sums with "value" (conditions are sub-functions)
By default, "union" is used for the function list at the top level.


```python
{script}
```

Again, if no specific time is mentioned, omit the "times" fields.
Think step by step about how to generate the heatmap matrix.

Use this JSON format:
```json
{{
  "time_buckets": ["Morning", "Afternoon", "Evening", "Night"],
  "functions": [
  {{
        "type": "intersection",
        "conditions: [
        {{
            "type": "weekends_only",
            "times": ["Afternoon", "Evening"],
            "value": 0.8,
            "years: [2019]
        }},
        {{
            "type": "month_range",
            "times": ["Afternoon", "Evening"],
            "start": "01-2019",
            "end": "12-2020",
            "value": 0.8,
            "years: [2019]
        }}
        ]
  }}
  ]
}}
```
"""


# %%
async def get_time_heatmap(phrase) -> Array2D[np.float32] | None:
    heatmap_json = await llm_model.generate_from_text(
        heatmap_prompt.format(phrase=phrase, script=script),
        model="gpt-4o"
    )
    # %%
    print("Heatmap JSON:", heatmap_json)
    matrix = None
    if not heatmap_json:
        print("[red]No heatmap JSON returned.[/red]")
        return None
    if "functions" in heatmap_json:
        if len(heatmap_json["functions"]) == 0:
            return None
        for function in heatmap_json["functions"]:
            new_matrix = generate_matrix_from_function_multi_years(
                fdef=function,
                years=function.get("years", [2019, 2020]),
            )
            if matrix is None:
                matrix = new_matrix
            else:
                matrix = np.maximum(matrix, new_matrix)

    elif "entries" in heatmap_json:
        if len(heatmap_json["entries"]) == 0:
            return None

        # fallback for sparse matrix (you already have this)
        matrix = np.zeros((len(TIME_BUCKETS), TOTAL_DAYS))
        for entry in heatmap_json["entries"]:
            row = TIME_TO_IDX[entry["time"]]
            col = date_str_to_doy(entry["date"])
            matrix[row, col] = entry["probability"]

    if matrix is None:
        print("No heatmap matrix generated.")
        return None

    # check if the matrix is empty
    if np.all(matrix == 0):
        print("The generated heatmap matrix is empty.")
        return None

    print("Generated heatmap matrix:")
    # generate a ascii table

    for year in range(2):
        print(f"Year {2019 + year}:")
        for row in matrix[:, year * 365 : (year + 1) * 365]:
            for value in row:
                box = " " if value < 0.1 else "█" if value >= 0.5 else "▒"
                print(box, end="")
            print()
        print()

    return matrix  # type: ignore

    # # %%
    # import seaborn as sns
    # import matplotlib.pyplot as plt

    # plt.figure(figsize=(14, 3))
    # sns.heatmap(matrix, cmap="YlGnBu", cbar=True,
    #             xticklabels=30, yticklabels=TIME_BUCKETS)
    # plt.title(f"Temporal Heatmap: {phrase}")
    # plt.xlabel("Day of Year")
    # plt.ylabel("Time of Day")
    # plt.tight_layout()
    # plt.show()

    # # %%


def get_time_info(photo_ids, photo_id_to_index):
    # check if the file exists
    try:
        with open("photo_times.pkl", "rb") as f:
            times = pickle.load(f)
            return times
    except FileNotFoundError:
        pass
    # Embed location data
    file = "/home/allie/data_mysceal/LSC23/vaisl_gps.csv"
    locations = pd.read_csv(file, dtype=str)

    times: list[Any] = [None for _ in range(len(photo_ids))]  # type: ignore
    for i in tqdm(range(len(locations))):
        try:
            row = locations.iloc[i]
            index = photo_id_to_index[row["ImageID"].split("/")[-1].split(".")[0]]
            timezone = row["new_timezone"]  # Europe/Berlin, etc.

            # Add local time
            image_id = row["ImageID"].split("/")[-1].split(".")[0]
            utc_time = datetime.datetime.strptime(image_id, "%Y%m%d_%H%M%S_000")
            utc_time = utc_time.replace(tzinfo=datetime.timezone.utc)
            try:
                local_time = utc_time.astimezone(ZoneInfo(timezone))
                times[index] = local_time
            except Exception:
                times[index] = utc_time

        except KeyError:
            continue

    # For None values, use the UTC time
    for i in range(len(times)):
        if times[i] is None:
            image_id = photo_ids[i].split("/")[-1].split(".")[0]
            utc_time = datetime.datetime.strptime(image_id, "%Y%m%d_%H%M%S_000")
            utc_time = utc_time.replace(tzinfo=datetime.timezone.utc)
            times[i] = utc_time
    # save the times to a file
    with open("photo_times.pkl", "wb") as f:
        pickle.dump(times, f)
    return times


def map_matrix_to_photos(
    matrix: np.ndarray, times: list[datetime.datetime]
) -> Array1D[np.float32]:
    probabilities = []
    for time in times:
        day_of_year = time.timetuple().tm_yday - 1
        time_of_day = "Morning"
        if time.hour < 12:
            time_of_day = "Morning"
        elif time.hour < 18:
            time_of_day = "Afternoon"
        elif time.hour < 22:
            time_of_day = "Evening"
        else:
            time_of_day = "Night"
        row = TIME_TO_IDX[time_of_day]
        year = time.year
        day_of_year += (year - 2019) * 365
        value = matrix[row, day_of_year]
        probabilities.append(value)
    probabilities = np.array(probabilities)
    return probabilities
