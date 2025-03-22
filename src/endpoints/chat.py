# file: src/endpoints/chat.py

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import os
import json
import pymongo
from typing import Optional, List, Dict
import uuid
from datetime import datetime
from openai import OpenAI

# ------------------ Existing Logic Imports ------------------
import sys
sys.path.append('.')
from src.LLM.RAG import (
    initialize_pinecone,
    query_pinecone,
    get_schedule_activity_summary,
    extract_progress,
    update_progress
)

# ------------------ FastAPI Setup ------------------
app = FastAPI()

# ------------------ Mongo Setup (Add a new 'conversations' collection) ------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://junryuf2:Sbdggw9gk6iCDKa4@dialog.yctqm.mongodb.net/?retryWrites=true&w=majority&appName=Dialog")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["test"]  # or your preferred DB name
collection_conversations = db["conversations"]  # new collection for chat conversations

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------ Existing Endpoints for Activities ------------------

class GetActivitiesRequest(BaseModel):
    project_name: str
    user_report: str
    top_k: Optional[int] = 10

class GetActivitiesResponse(BaseModel):
    summary: str
    matched_activities: List[Dict]

@app.post("/api/chat/get_activities", response_model=GetActivitiesResponse)
def get_activities(body: GetActivitiesRequest):
    index = initialize_pinecone()
    results = query_pinecone(
        index=index,
        query_text=body.user_report,
        namespace=body.project_name,
        top_k=body.top_k
    )
    matches = results.get("matches", [])

    summary_text = get_schedule_activity_summary(body.user_report, matches)

    matched_activities_data = []
    for match in matches:
        metadata = match.get("metadata", {})
        activity_name = metadata.get("name", "N/A")
        object_id = metadata.get("ObjectId", None)

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

class UpdateActivitiesRequest(BaseModel):
    updates: List[Dict]

class UpdateActivitiesResponse(BaseModel):
    updated_activities: List[Dict]

@app.post("/api/chat/update_activities", response_model=UpdateActivitiesResponse)
def update_activities(body: UpdateActivitiesRequest):
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
            "reason": "updated" if success else "nothing changed"
        })

    return {
        "updated_activities": updated_activities_info
    }

# ------------------ New Chat Conversation Endpoint ------------------
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatConversationRequest(BaseModel):
    session_id: Optional[str] = None  # Make sure to default to None
    user_message: str

class ChatConversationResponse(BaseModel):
    session_id: str
    messages: str  # List[ChatMessage]

@app.post("/api/chat/conversation", response_model=ChatConversationResponse)
def conversation(body: ChatConversationRequest):
    """
    Maintains a conversation with an AI model, storing chat history in MongoDB.
    """

    # 1) Create/find conversation
    if body.session_id:
        convo_doc = collection_conversations.find_one({"session_id": body.session_id})
        if convo_doc is None:
            # If session_id is provided but not found, we treat it as new
            session_id = body.session_id
            convo_doc = {
                "session_id": session_id,
                "messages": [
                    {"role": "system", "content": "You are a helpful construction assistant."}
                ],
                "last_updated": datetime.utcnow()
            }
            collection_conversations.insert_one(convo_doc)
        else:
            session_id = body.session_id
    else:
        # session_id was not provided -> create a new one
        session_id = str(uuid.uuid4())
        convo_doc = {
            "session_id": session_id,
            "messages": [
                {"role": "system", "content": "You are a helpful construction assistant."}
            ],
            "last_updated": datetime.utcnow()
        }
        collection_conversations.insert_one(convo_doc)

    # 2) Append user's message
    messages = convo_doc["messages"]
    messages.append({"role": "user", "content": body.user_message})

    # 3) Call OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )
    assistant_content = response.choices[0].message.content

    # 4) Append assistant message & update DB
    messages.append({"role": "assistant", "content": assistant_content})
    collection_conversations.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "messages": messages,
                "last_updated": datetime.utcnow()
            }
        }
    )

    # 5) return the response
    return {
        "session_id": session_id,
        "messages": assistant_content
    }


# ------------------ Run the Server ------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
