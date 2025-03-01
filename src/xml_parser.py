import xml.etree.ElementTree as ET
import json

def get_namespace(xml_file):
    """Extracts the XML namespace dynamically from the file."""
    with open(xml_file, "r") as f:
        for line in f:
            if "xmlns" in line:
                start = line.find("xmlns=")
                if start != -1:
                    quote_type = '"' if '"' in line[start+6:] else "'"
                    return line[start+6:].split(quote_type)[1]
    return None  # Return None if no namespace is found

def convert_xml_to_json(xml_file, json_file):
    """Converts XML data to JSON."""
    tree = ET.parse(xml_file)
    root = tree.getroot()

    namespace = get_namespace(xml_file)
    ns = {'ns': namespace} if namespace else {}

    # Step 1: Build a dictionary of WBSObjectId -> WBS Details
    wbs_dict = {}
    for wbs in root.findall(".//ns:WBS", ns):
        obj_id = wbs.find("ns:ObjectId", ns)
        wbs_id = obj_id.text if obj_id is not None and obj_id.text else "NaN"
        name = wbs.find("ns:Name", ns)
        wbs_name = name.text if name is not None and name.text else "NaN"
        parent_id = wbs.find("ns:ParentObjectId", ns)
        parent_id = parent_id.text if parent_id is not None and parent_id.text else "NaN"

        wbs_dict[wbs_id] = {"name": wbs_name, "parent_id": parent_id}

    # Function to build WBS hierarchy
    def get_wbs_hierarchy(wbs_id):
        """Recursively builds the WBS hierarchy based on ParentObjectId."""
        hierarchy = []
        while wbs_id in wbs_dict and wbs_dict[wbs_id]["parent_id"] != "NaN":
            hierarchy.insert(0, wbs_dict[wbs_id]["name"])  # Insert at beginning
            wbs_id = wbs_dict[wbs_id]["parent_id"]
        if wbs_id in wbs_dict:  # Include the top-level WBS
            hierarchy.insert(0, wbs_dict[wbs_id]["name"])
        return hierarchy

    # Step 2: Build a dictionary of Activity ObjectId -> Name
    activity_dict = {}
    for activity in root.findall(".//ns:Activity", ns):
        obj_id = activity.find("ns:ObjectId", ns)
        name = activity.find("ns:Name", ns)

        if obj_id is not None and name is not None:
            activity_dict[obj_id.text] = name.text

    # Step 3: Extract relationships and map to activity names
    relationships = {}

    for relationship in root.findall(".//ns:Relationship", ns):
        pred_act_id = relationship.find("ns:PredecessorActivityObjectId", ns)
        succ_act_id = relationship.find("ns:SuccessorActivityObjectId", ns)
        lag = relationship.find("ns:Lag", ns)
        lag_value = lag.text if lag is not None and lag.text else "NaN"
        pred_id = pred_act_id.text if pred_act_id is not None else "NaN"
        succ_id = succ_act_id.text if succ_act_id is not None else "NaN"

        pred_name = activity_dict.get(pred_id, "Unknown Activity")
        succ_name = activity_dict.get(succ_id, "Unknown Activity")

        if pred_id != "NaN":
            if succ_id not in relationships:
                relationships[succ_id] = {"predecessor": [], "successor": []}
            relationships[succ_id]["predecessor"].append({"ObjectId": pred_id, "name": pred_name, "lag": lag_value})

        if succ_id != "NaN":
            if pred_id not in relationships:
                relationships[pred_id] = {"predecessor": [], "successor": []}
            relationships[pred_id]["successor"].append({"ObjectId": succ_id, "name": succ_name, "lag": lag_value})

    # Step 4: Extract activities with predecessors and successors
    activities = []
    for i, activity in enumerate(root.findall(".//ns:Activity", ns), start=1):
        obj_id = activity.find("ns:ObjectId", ns)
        name = activity.find("ns:Name", ns)
        planned_duration = activity.find("ns:PlannedDuration", ns)
        planned_start_date = activity.find("ns:PlannedStartDate", ns)
        planned_end_date = activity.find("ns:PlannedFinishDate", ns)
        early_start_date = activity.find("ns:RemainingEarlyStartDate", ns)
        early_finish_date = activity.find("ns:RemainingEarlyFinishDate", ns)
        late_start_date = activity.find("ns:RemainingLateStartDate", ns)
        late_finish_date = activity.find("ns:RemainingLateFinishDate", ns)
        actual_start_date = activity.find("ns:ActualStartDate", ns)
        actual_finish_date = activity.find("ns:ActualFinishDate", ns)

        obj_id_text = obj_id.text if obj_id is not None else "NaN"
        wbs_id = activity.find("ns:WBSObjectId", ns)
        wbs_id_text = wbs_id.text if wbs_id is not None else "NaN"
        wbs_hierarchy = get_wbs_hierarchy(wbs_id_text)  # Build WBS hierarchy

        activities.append({
            i: {
                "name": name.text if name is not None else "NaN",
                "ObjectId": obj_id_text,
                "actual_start": actual_start_date.text if actual_start_date is not None else "NaN",
                "actual_end": actual_finish_date.text if actual_finish_date is not None else "NaN",
                "planned_duration": planned_duration.text if planned_duration is not None else "NaN",
                "planned_start_date": planned_start_date.text if planned_start_date is not None else "NaN",
                "planned_end_date": planned_end_date.text if planned_end_date is not None else "NaN",
                "early_finish_date": early_finish_date.text if early_finish_date is not None else "NaN",
                "early_start_date": early_start_date.text if early_start_date is not None else "NaN",
                "late_finish_date": late_finish_date.text if late_finish_date is not None else "NaN",
                "late_start_date": late_start_date.text if late_start_date is not None else "NaN",
                "predecessor": relationships.get(obj_id_text, {}).get("predecessor", []),
                "successor": relationships.get(obj_id_text, {}).get("successor", []),
                "wbs": wbs_hierarchy
            }
        })

    # Convert to JSON
    with open(json_file, "w") as f:
        json.dump(activities, f, indent=4)

    print(f"✅ JSON data has been saved to {json_file}")
