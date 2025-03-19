import os
import json
from openai import OpenAI
from pinecone import Pinecone

# Set your API keys here
OPENAI_API_KEY = "your API"
PINECONE_API_KEY = "pcsk_49xJ6R_79kmGWc75R6NUBvPQssUoEiDMRrmjJb3zNDdSsodUgiRM71Q6pnq9NFog5Cnr3X"
INDEX_NAME = "activities-index"
client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    """
    Given a text string, returns its embedding using the OpenAI text-embedding-002 model.
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    # The API returns a list of embeddings for each input item; we use the first one.
    embedding = response.data[0].embedding
    return embedding

def load_activities(file_path):
    """
    Loads activities from a JSON file and returns a list of inner dictionaries.
    Assumes the JSON is an array of objects with a single key.
    """
    with open(file_path, "r") as f:
        activities_json = json.load(f)

    activities = []
    for item in activities_json:
        # Each item is expected to be a dictionary with a single key
        for key, value in item.items():
            activities.append(value)
    return activities

def initialize_pinecone():
    """
    Initializes Pinecone and ensures that the desired index exists.
    The dimension for text-embedding-3-small is 1536.
    """
    pc = Pinecone(api_key=PINECONE_API_KEY, host="https://activities-index-ku54fn2.svc.aped-4627-b74a.pinecone.io")
    return pc.Index(INDEX_NAME)


def sanitize_metadata(metadata):
    """
    Returns a new dictionary with only keys that have acceptable metadata values.
    If a value is a list of dictionaries (e.g., for keys like 'predecessor' or 'successor'),
    it converts each dictionary into a formatted string.
    """
    new_metadata = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            # If it's a list and all items are dicts, convert each dict to a string.
            if value and all(isinstance(item, dict) for item in value):
                new_metadata[key] = [
                    f"{item.get('ObjectId', '')}-{item.get('name', '')}-lag:{item.get('lag', '')}"
                    for item in value
                ]
            else:
                new_metadata[key] = value
        else:
            new_metadata[key] = value
    return new_metadata


def upsert_activities(index, activities, namespace):
    """
    Converts each activity name into an embedding vector and upserts the record into Pinecone.
    The activity's "ObjectId" is used as the unique vector id.
    """
    vectors = []
    for activity in activities:
        activity_name = activity.get("name", "")
        print("activity_name: ", activity_name)
        embedding = get_embedding(activity_name)

        vector_id = activity.get("ObjectId")
        if not vector_id:
            print("Skipping an activity without an ObjectId.")
            continue
        clean_metadata = sanitize_metadata(activity)
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": clean_metadata
        })
    batch_size = 50
    # Batch the upsert to avoid exceeding message length limits
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        upsert_response = index.upsert(vectors=batch, namespace=namespace)
        print(f"Upserted batch {i // batch_size + 1}: {len(batch)} vectors.")
        print("Batch upsert response:", upsert_response)


def main():
    file_name = "projectX.json"
    project_name = os.path.splitext(os.path.basename(file_name))[0]
    print(f"Project name: {project_name}")
    activities = load_activities(file_name)
    index = initialize_pinecone()
    upsert_activities(index, activities, namespace=project_name)

if __name__ == "__main__":
    main()
