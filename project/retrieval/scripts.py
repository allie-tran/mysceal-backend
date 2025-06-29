from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
from visual.types import Array2D

# --- CONFIG ---

TIME_BUCKETS = ["Morning", "Afternoon", "Evening", "Night"]
TIME_TO_IDX = {name: i for i, name in enumerate(TIME_BUCKETS)}

# --- HELPERS ---


def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def date_str_to_doy(date_str: str) -> int:
    """Convert 'DD-MM' to day-of-year index (0-based) for given year."""
    dt = datetime.strptime(f"{date_str}", "%d-%m-%Y")
    year = dt.year
    day_offset = sum(366 if is_leap_year(y) else 365 for y in YEARS if y < year)
    return dt.timetuple().tm_yday - 1 + day_offset


def weekday_str_to_index(name: str) -> int:
    """Convert weekday name to index (Monday = 0)."""
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ].index(name.lower())


# --- MAIN FUNCTION ---
import calendar


def max_day_of_month(month: int, year: int) -> int:
    """Return number of days in a given month and year."""
    return calendar.monthrange(year, month)[1]


def safe_closest_date_MM_YY(date_str: str, start: bool = True) -> datetime:
    month, year = map(int, date_str.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {month}")
    day = 1 if start else max_day_of_month(month, year)
    return datetime(year, month, day)

def safe_closest_date_DD_MM(date_str: str, year: int = 2019) -> datetime:
    day, month = map(int, date_str.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {month}")
    if not 1 <= day <= max_day_of_month(month, 2023):  # Assuming year is not critical
        raise ValueError(f"Invalid day: {day}")
    return datetime(year, month, day)


YEARS = [2019, 2020]
TIME_BUCKETS = ["Morning", "Afternoon", "Evening", "Night"]
time_buckets = TIME_BUCKETS
TOTAL_DAYS = sum(366 if is_leap_year(y) else 365 for y in YEARS)


def generate_matrix_from_function_multi_years(
    fdef: Dict, years: List[int]
) -> Array2D[np.float32]:
    """
    Generate a 4 x N matrix for multiple years from a temporal function definition.
    Each column corresponds to a day, covering all days in the specified years.
    """
    matrix: Array2D[np.float32] = np.zeros(
        (len(time_buckets), TOTAL_DAYS), dtype=np.float32
    )
    value = fdef.get("value", 1.0)
    times = fdef.get("times", time_buckets)
    type_ = fdef["type"]
    years = [year for year in years if year in YEARS]  # Filter valid years

    for year in years:
        days_in_year = 366 if is_leap_year(year) else 365
        day_offset = sum(366 if is_leap_year(y) else 365 for y in YEARS if y < year)
        print(f"Processing year {year} with {days_in_year} days, offset {day_offset}")

        if type_ in {
            "weekends_only",
            "weekdays_only",
            "daily_pattern",
            "weekday_pattern",
            "month_range",
            "specific_dates",
            "year",
        }:
            if type_ == "weekends_only":
                for day in range(days_in_year):
                    date = datetime(year, 1, 1) + timedelta(days=day)
                    # Check if it's a weekend
                    if date.weekday() in (5, 6):
                        for t in times:
                            matrix[TIME_TO_IDX[t], day_offset + day] = value
            elif type_ == "weekdays_only":
                for day in range(days_in_year):
                    date = datetime(year, 1, 1) + timedelta(days=day)
                    # Check if it's a weekday (Monday to Friday)
                    if date.weekday() >= 0 and date.weekday() <= 4:
                        for t in times:
                            matrix[TIME_TO_IDX[t], day_offset + day] = value
            elif type_ == "daily_pattern":
                for day in range(days_in_year):
                    for t in times:
                        matrix[TIME_TO_IDX[t], day_offset + day] = value
            elif type_ == "weekday_pattern":
                for day in range(days_in_year):
                    date = datetime(year, 1, 1) + timedelta(days=day)
                    weekdays = [weekday_str_to_index(d) for d in fdef["days"]]
                    if date.weekday() in weekdays:
                        for t in times:
                            matrix[TIME_TO_IDX[t], day_offset + day] = value
            elif type_ == "month_range":
                try:
                    start = safe_closest_date_MM_YY(fdef["start"], start=True)
                    end = safe_closest_date_MM_YY(fdef["end"], start=False)
                except ValueError:
                    print(
                        f"Invalid date format in month_range for year {year}: {fdef['start']}, {fdef['end']}"
                    )
                    # try the nearest valid date
                    start = datetime(year, 1, 1)
                    end = datetime(year, 12, 31)

                index = []
                for day in range(days_in_year):
                    date = datetime(year, 1, 1) + timedelta(days=day)
                    if start <= date <= end:
                        index.append(day + day_offset)
                        for t in times:
                            matrix[TIME_TO_IDX[t], day_offset + day] = value
                print(index)

            elif type_ == "specific_dates":
                for day in range(days_in_year):
                    date = datetime(year, 1, 1) + timedelta(days=day)
                    # Check if the date matches any specified dates
                    if date.strftime("%d-%m") in fdef["dates"]:
                        for t in times:
                            matrix[TIME_TO_IDX[t], day_offset + day] = value
            elif type_ == "year":
                # This is a special case where the entire year is selected
                for day in range(days_in_year):
                    for t in times:
                        matrix[TIME_TO_IDX[t], day_offset + day] = value

        elif type_ == "day_range":
            # start = fdef["start_day"]
            # end = fdef["end_day"]
            start = safe_closest_date_DD_MM(fdef["start"], year)
            end = safe_closest_date_DD_MM(fdef["end"], year)
            for day in range(days_in_year):
                date = datetime(year, 1, 1) + timedelta(days=day)
                if start <= date <= end:
                    for t in times:
                        matrix[TIME_TO_IDX[t], day_offset + day] = value

    if type_ == "intersection":
        # Recursive intersection logic
        sub_matrices = [
            generate_matrix_from_function_multi_years(sub, sub.get("years", years))
            for sub in fdef["conditions"]
        ]
        intersection = np.min(np.stack(sub_matrices), axis=0)
        for i, t in enumerate(time_buckets):
            if t in times:
                matrix[i, :] = intersection[i, :] * value

    elif type_ == "union":
        # Recursive union logic
        sub_matrices = [
            generate_matrix_from_function_multi_years(sub, sub.get("years", years))
            for sub in fdef["conditions"]
        ]
        union = np.max(np.stack(sub_matrices), axis=0)
        for i, t in enumerate(time_buckets):
            if t in times:
                matrix[i, :] = union[i, :] * value

    return matrix
