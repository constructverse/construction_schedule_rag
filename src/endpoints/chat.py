# file: src/endpoints/chat.py

from fastapi import FastAPI, Body
from pydantic import BaseModel
import uvicorn
import os
import json
import pymongo
from typing import Optional, List, Dict

# ------------------ Existing Logic Imports ------------------ 
# Adjust these imports to point to where your existing functions live.
# For example, if they're in src/llm/rag.py, do:
# from src.llm.rag import (
#     initialize_pinecone, query_pinecone, get_schedule_activity_summary,
#     extract_progress, update_progress
# )

import sys
sys.path.append('.')
from src.LLM.RAG import (
    initialize_pinecone, query_pinecone, get_schedule_activity_summary,
    extract_progress, update_progress
)

# ------------------ FastAPI Setup ------------------
app = FastAPI()



class GetActivitiesRequest(BaseModel):
    project_name: str
    user_report: str
    top_k: Optional[int] = 10

class GetActivitiesResponse(BaseModel):
    summary: str
    matched_activities: List[Dict]  # Each element: { "id", "name", "detected_progress": ..., ...}


# ------------------ Endpoint 1: Retrieve Matches & Detected Progress ------------------

@app.post("/api/chat/get_activities", response_model=GetActivitiesResponse)
def get_activities(body: GetActivitiesRequest):
    """
    This endpoint takes the user's report and returns the most relevant schedule activities.
    We also attempt to auto-detect progress for each activity (if possible).
    The client (front-end) can then choose which ones to update.
    """
    # 1) Initialize and Query Pinecone
    index = initialize_pinecone()
    results = query_pinecone(
        index=index,
        query_text=body.user_report,
        namespace=body.project_name,
        top_k=body.top_k
    )
    matches = results.get("matches", [])

    # 2) Summarize matches
    summary_text = get_schedule_activity_summary(body.user_report, matches)

    # 3) Build response data
    matched_activities_data = []
    for match in matches:
        metadata = match.get("metadata", {})
        activity_name = metadata.get("name", "N/A")
        object_id = metadata.get("ObjectId", None)

        # Attempt to auto-detect progress (could be None)
        detected_progress = extract_progress(body.user_report, activity_name)

        matched_activities_data.append({
            "id": match.get("id"),
            "object_id": object_id,
            "name": activity_name,
            "detected_progress": detected_progress
        })

    return {
        "summary": summary_text,
        "matched_activities": matched_activities_data
    }


# ------------------ Endpoint 2: Update Activities ------------------

class UpdateActivitiesRequest(BaseModel):
    updates: List[Dict]
    """
    Example of 'updates':
      [
        {
          "object_id": "abc123",
          "name": "Pouring Concrete",
          "progress": 60.0
        },
        {
          "object_id": "xyz789",
          "name": "Digging Foundation",
          "progress": 25.0
        }
      ]
    """

class UpdateActivitiesResponse(BaseModel):
    updated_activities: List[Dict]
    """
    Each element in 'updated_activities':
      {
        "object_id": ...,
        "success": True/False,
        "reason": ...,
      }
    """


@app.post("/api/chat/update_activities", response_model=UpdateActivitiesResponse)
def update_activities(body: UpdateActivitiesRequest):
    """
    This endpoint receives a list of activities to update, with the user’s chosen
    progress values. We then attempt to update each in the database.
    """
    updated_activities_info = []
    for item in body.updates:
        object_id = item.get("object_id")
        progress_val = item.get("progress")
        if not object_id or progress_val is None:
            updated_activities_info.append({
                "object_id": object_id,
                "success": False,
                "reason": "missing object_id or progress"
            })
            continue

        success = update_progress(object_id, progress_val)
        updated_activities_info.append({
            "object_id": object_id,
            "success": success,
            "reason": "nothing changed" if not success else "updated"
        })

    return {
        "updated_activities": updated_activities_info
    }


# ------------------ Run the Server ------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)