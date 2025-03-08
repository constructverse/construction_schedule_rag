
# -*- coding: utf-8 -*-

"""

Created by: Yoonhwa Jung

"""

import json
from datetime import datetime, timedelta

def load_json(json_file):
    """Loads JSON file and returns data."""
    with open(json_file, "r") as f:
        return json.load(f)

def calculate_end_date(start_date_str, duration_str):
    """Calculates end date if missing, based on planned start date and duration."""
    if not start_date_str or start_date_str == "NaN" or not duration_str or duration_str == "NaN":
        return None  # Cannot calculate without both values

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S").date()
        duration = int(duration_str)
        return start_date + timedelta(days=duration)
    except (ValueError, TypeError):
        return None  # In case of invalid format

def is_activity_happening(activity, target_date):
    """Checks if the target date falls within the activity duration."""
    date_fields = [
        ("planned_start_date", "planned_end_date", "planned_duration"),
        ("early_start_date", "early_finish_date", "planned_duration"),
        ("late_start_date", "late_finish_date", "planned_duration"),
        ("actual_start", "actual_end", "planned_duration")
    ]

    for start_field, end_field, duration_field in date_fields:
        start_date_str = activity.get(start_field, "NaN")
        end_date_str = activity.get(end_field, "NaN")

        start_date = None
        end_date = None

        # Parse start_date if it's available
        if start_date_str and start_date_str != "NaN":
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S").date()
            except (ValueError, TypeError):
                start_date = None  # Handle invalid dates

        # Parse end_date if it's available
        if end_date_str and end_date_str != "NaN":
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S").date()
            except (ValueError, TypeError):
                end_date = None  # Handle invalid dates

        # If end_date is missing, calculate it using planned_duration
        if end_date is None:
            end_date = calculate_end_date(start_date_str, activity.get(duration_field, "NaN"))

        # If both start and end dates are valid, check if the target date falls within the range
        if start_date and end_date and start_date <= target_date <= end_date:
            return True

    return False

def filter_activities_by_date(json_file, target_date_str):
    """Filters activities happening on the given date."""
    data = load_json(json_file)
    target_date = datetime.strptime(target_date_str, "%m/%d/%Y").date()

    filtered_activities = []

    for activity_dict in data:
        for _, activity in activity_dict.items():  # Activities are stored in nested dictionaries
            if is_activity_happening(activity, target_date):
                filtered_activities.append(activity)

    return filtered_activities

