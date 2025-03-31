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


# ------------------ Update Activities ------------------    

class UpdateActivitiesRequest(BaseModel):
    updates: List[Dict]  # each Dict should have {object_id, name, progress}

class UpdateActivitiesResponse(BaseModel):
    updated_activities: List[Dict]

@app.post("/api/chat/update_activities", response_model=UpdateActivitiesResponse)
def update_activities(body: UpdateActivitiesRequest):
    """
    For each requested update, we use extract_progress to interpret
    the textual progress in 'progress'. Then update the DB accordingly.
    """
    updated_activities_info = []
    for item in body.updates:
        object_id = item.get("object_id")
        activity_name = item.get("name", "")
        # The user might pass "progress" as a free-text description (e.g. "80%", "almost done", etc.)
        progress_text = str(item.get("progress", ""))

        if not object_id:
            updated_activities_info.append({
                "object_id": None,
                "success": False,
                "reason": "missing object_id"
            })
            continue

        # Use the GPT-based function to interpret the numeric progress
        interpreted_progress = extract_progress(progress_text, activity_name)
        if interpreted_progress is None:
            updated_activities_info.append({
                "object_id": object_id,
                "success": False,
                "reason": f"Could not parse numeric progress from '{progress_text}'"
            })
            continue

        # Update the DB
        success = update_progress(object_id, interpreted_progress)
        updated_activities_info.append({
            "object_id": object_id,
            "success": success,
            "reason": "updated" if success else "no change"
        })

    return {
        "updated_activities": updated_activities_info
    }


# ------------------ New get_summary Endpoint ------------------ #
class GetSummaryRequest(BaseModel):
    project_name: str
    user_text: str
    top_k: Optional[int] = 5

class GetSummaryResponse(BaseModel):
    summary: str

@app.post("/api/chat/get_summary", response_model=GetSummaryResponse)
def get_summary(body: GetSummaryRequest):
    """
    Retrieves top-k relevant documents or schedule activities from Pinecone 
    and returns only a summarized result, without the matched activities list.
    """
    index = initialize_pinecone()
    results = query_pinecone(
        index=index,
        query_text=body.user_text,
        namespace=body.project_name,
        top_k=body.top_k
    )
    matches = results.get("matches", [])
    summary_text = get_schedule_activity_summary(body.user_text, matches)
    return {"summary": summary_text}




# ------------------ New Conversation Endpoint ------------------ #

def classify_query(user_msg: str) -> str:
    """
    Uses GPT to classify whether the user_msg is about general knowledge 
    or specifically about the project (construction) context.
    Return 'general' or 'specific'.
    """
    classification_prompt = (
        "You are a classifier. Given a user question, decide if it is "
        "general knowledge or specific to project construction activities.\n"
        "Return only the single word 'general' or 'specific'.\n"
        f"Question: {user_msg}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Classify query."},
            {"role": "user", "content": classification_prompt}
        ],
        temperature=0.0,
        max_tokens=10
    )
    raw_text = response.choices[0].message.content.strip().lower()
    # Very simple check
    if "specific" in raw_text:
        return "specific"
    return "general"


def answer_general_question(messages: List[Dict]) -> str:
    """
    If the user question is 'general', we feed the conversation so far
    directly into GPT (gpt-4, for example) for an answer.
    """
    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo"
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )
    return response.choices[0].message.content


def answer_specific_question(user_msg: str, project_name: str = "output") -> str:
    """
    If the user question is 'specific', we do a retrieval from Pinecone (RAG)
    and then have GPT generate the final answer from the context.
    """
    # 1) Retrieve relevant info from Pinecone
    index = initialize_pinecone()
    results = query_pinecone(index, user_msg, namespace=project_name, top_k=5)
    matches = results.get("matches", [])

    # 2) Build the context string for GPT
    context_str = ""
    for i, match in enumerate(matches, start=1):
        meta = match.get("metadata", {})
        context_str += f"Activity {i}: {meta.get('name', 'Unknown')}\n"
        # You can add more metadata if needed

    # 3) Compose prompt for GPT
    rag_prompt = (
        "You are a helpful construction assistant. The user asked a question "
        "specific to the project. We have some retrieved context from a schedule:\n\n"
        f"{context_str}\n"
        f"User question: {user_msg}\n\n"
        "Please answer accurately based on the context."
    )

    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "Provide a project-specific answer from the context."},
            {"role": "user", "content": rag_prompt}
        ],
        temperature=0.7,
        max_tokens=512
    )
    return response.choices[0].message.content


# Request/Response models
class ChatConversationRequest(BaseModel):
    session_id: Optional[str] = None
    user_message: str
    project_name: Optional[str] = "output"

class ChatConversationResponse(BaseModel):
    session_id: str
    task: str      # "general" or "specific"
    content: str   # The final GPT answer

@app.post("/api/chat/conversation", response_model=ChatConversationResponse)
def conversation(body: ChatConversationRequest):
    """
    1) Loads or creates a conversation document from MongoDB.
    2) Classifies the user's message as either 'general' or 'specific'.
    3) If 'general', use GPT directly to answer. 
       If 'specific', do RAG from Pinecone + GPT for final answer.
    4) Store all messages in MongoDB and return a JSON object:
         { "task": "general" or "specific", "content": "<assistant reply>" }
    """
    # 1) Create/find conversation doc
    if body.session_id:
        convo_doc = collection_conversations.find_one({"session_id": body.session_id})
        if convo_doc is None:
            # If session_id provided but not found -> create new
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
        print("Creating new conversation document since no session_id was provided.")
        # No session_id -> create new
        session_id = str(uuid.uuid4())
        print(f"Generated new session_id: {session_id}")
        convo_doc = {
            "session_id": session_id,
            "messages": [
                {"role": "system", "content": "You are a helpful construction assistant."}
            ],
            "last_updated": datetime.utcnow()
        }
        print(f"New conversation document created with session_id: {session_id}")
        collection_conversations.insert_one(convo_doc)
        

    # 2) Append user's message
    messages = convo_doc["messages"]
    messages.append({"role": "user", "content": body.user_message})

    # 3) Classify user question
    classification = classify_query(body.user_message)  # "general" or "specific"

    print(f"Classified user message: '{body.user_message}' as '{classification}'")

    # 4) Generate final answer
    if classification == "general":
        assistant_content = answer_general_question(messages)
    else:
        # classification == "specific"
        assistant_content = answer_specific_question(body.user_message, body.project_name)

    # Append assistant answer to conversation messages
    messages.append({"role": "assistant", "content": assistant_content})

    # Update DB
    collection_conversations.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "messages": messages,
                "last_updated": datetime.utcnow()
            }
        }
    )

    # 5) Return JSON with "task" and "content"
    return {
        "session_id": session_id,
        "task": classification,
        "content": assistant_content
    }



# ------------------ Run the Server ------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
