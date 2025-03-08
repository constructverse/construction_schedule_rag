import os
import json
from datetime import datetime

import sys
sys.path.append(".")
from src.xml_parser import convert_xml_to_json
from src.filter_by_date import filter_activities_by_date
from src.visualized_filterd_activities import visualize_activities
from src.build_graph import build_graph

# File paths
DATA_FOLDER = "src/data"
XML_FILE = os.path.join(DATA_FOLDER, "UofMAthletesVillage.xml")
print(XML_FILE)
base_name = os.path.splitext(XML_FILE)[0]
JSON_FILE = os.path.join(f"{base_name}_output.json")
print(JSON_FILE)
FILTERED_JSON_FILE = os.path.join(f"{base_name}_filtered_activities.json")


def main():
    """Runs XML to JSON conversion, filters activities, and visualizes the data."""

    # Step 1: Convert XML to JSON
    print("\n[Step 1] Processing XML to JSON...")
    convert_xml_to_json(XML_FILE, JSON_FILE)

    # Step 2: Filter Activities by Date
    target_date = input("\nEnter a date to filter activities (MM/DD/YYYY): ").strip()
    try:
        datetime.strptime(target_date, "%m/%d/%Y")  # Validate date format
    except ValueError:
        print("❌ Invalid date format. Please enter in MM/DD/YYYY format.")
        return

    print(f"\n[Step 2] Filtering activities happening on {target_date}...")
    filtered_activities = filter_activities_by_date(JSON_FILE, target_date)

    if filtered_activities:
        with open(FILTERED_JSON_FILE, "w") as f:
            json.dump(filtered_activities, f, indent=4)
        print(f"✅ Filtered activities saved to {FILTERED_JSON_FILE}")
    else:
        print("❌ No activities found for the given date.")
        return

    # Step 3: Visualize Activities
    print("\n[Step 3] Visualizing activities...")
    visualize_activities(FILTERED_JSON_FILE, target_date)

    # step 4: Build Graph
    print("\n[Step 4] Building graph...")
    build_graph(FILTERED_JSON_FILE)


if __name__ == "__main__":
    main()
