import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

def load_json(json_file):
    """Loads JSON file and returns data."""
    with open(json_file, "r") as f:
        return json.load(f)

def calculate_end_date(start_date, duration_str):
    """Calculates end date if missing, based on start date and duration."""
    if start_date is None or duration_str in ["NaN", None]:  # Handle None values
        return None  # Cannot calculate without both values

    try:
        duration = int(duration_str)
        return start_date + timedelta(days=duration)
    except (ValueError, TypeError):
        return None  # If duration is invalid

def get_valid_dates(activity):
    """Returns the best available start and end dates (Actual → Planned)."""
    # Try actual dates first
    start_date_str = activity.get("actual_start", "NaN")
    end_date_str = activity.get("actual_end", "NaN")  # May be None
    duration_str = activity.get("planned_duration", "NaN")  # Use duration if needed

    # If actual dates are missing, use planned dates
    if start_date_str in ["NaN", None]:
        start_date_str = activity.get("planned_start_date", "NaN")
    if end_date_str in ["NaN", None]:  # If null, use planned dates
        end_date_str = activity.get("planned_end_date", "NaN")

    # Convert start_date if valid
    start_date = None
    if start_date_str not in ["NaN", None]:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S").date()
        except (ValueError, TypeError):
            start_date = None  # Handle invalid formats

    # Convert end_date if valid
    end_date = None
    if end_date_str not in ["NaN", None]:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S").date()
        except (ValueError, TypeError):
            end_date = None  # Handle invalid formats

    # If end_date is missing, calculate using planned_duration
    if end_date is None:
        end_date = calculate_end_date(start_date, duration_str)

    return start_date, end_date

def extract_activity_data(filtered_activities):
    """Extracts start dates, end dates, and names for plotting."""
    activity_names = []
    start_dates = []
    end_dates = []

    for activity in filtered_activities:
        name = activity["name"]
        start_date, end_date = get_valid_dates(activity)

        if start_date and end_date:
            activity_names.append(name)
            start_dates.append(start_date)
            end_dates.append(end_date)

    return activity_names, start_dates, end_dates

def visualize_activities(json_file, target_date_str):
    """Creates a bar chart for activities happening on the given date."""
    filtered_activities = load_json(json_file)
    activity_names, start_dates, end_dates = extract_activity_data(filtered_activities)

    if not activity_names:
        print("No activities to visualize.")
        return

    # Convert target date to datetime
    target_date = datetime.strptime(target_date_str, "%m/%d/%Y").date()

    # Set up figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each activity as a horizontal bar
    for i, (name, start, end) in enumerate(zip(activity_names, start_dates, end_dates)):
        ax.barh(name, (end - start).days, left=start, color="skyblue", edgecolor="black")

    # Highlight the target date
    ax.axvline(target_date, color="red", linestyle="--", label=f"Target Date: {target_date}")

    # Format x-axis as dates
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45)

    # Labels and title
    ax.set_xlabel("Date")
    ax.set_ylabel("Activities")
    ax.set_title(f"Activities Happening on {target_date}")
    ax.legend()

    # Show plot
    plt.tight_layout()
    plt.show()