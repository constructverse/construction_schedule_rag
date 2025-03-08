import json

# Load JSON file
with open("output.json", "r", encoding="utf-8") as file:
    data = json.load(file)

text_data = ""

# Convert each schedule item into a readable text format
for item in data:
    for key, value in item.items():
        text_data += f"Task Name: {value['name']}\n"
        text_data += f"Object ID: {value['ObjectId']}\n"
        text_data += f"Percentage Complete: {value['Percentage_complete']}%\n"
        text_data += f"Planned Start: {value['planned_start_date']}\n"
        text_data += f"Planned End: {value['planned_end_date']}\n"
        text_data += f"Duration: {value['planned_duration']} hours\n"

        # Predecessors
        if value.get("predecessor"):
            text_data += "Predecessors: " + ", ".join(
                [pred["name"] for pred in value["predecessor"]]
            ) + "\n"

        # Successors
        if value.get("successor"):
            text_data += "Successors: " + ", ".join(
                [succ["name"] for succ in value["successor"]]
            ) + "\n"

        text_data += "-" * 50 + "\n"

# Save to a text file
with open("processed_schedule.txt", "w", encoding="utf-8") as file:
    file.write(text_data)

print("Preprocessing complete. Saved as processed_schedule.txt")