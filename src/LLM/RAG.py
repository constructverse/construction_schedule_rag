# src/LLM/RAG.py

import os
import json
# from openai import openAI as OpenAI
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import pymongo
from pdb import set_trace as bp
import certifi

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key")

PINECONE_API_KEY = "pcsk_49xJ6R_79kmGWc75R6NUBvPQssUoEiDMRrmjJb3zNDdSsodUgiRM71Q6pnq9NFog5Cnr3X"
INDEX_NAME = "activities-index"
client = OpenAI(api_key=OPENAI_API_KEY)
OpenAI.api_key = OPENAI_API_KEY

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://junryuf2:Sbdggw9gk6iCDKa4@dialog.yctqm.mongodb.net/?retryWrites=true&w=majority&appName=Dialog")
MONGO_DB_NAME = "test"
MONGO_COLLECTION_NAME = "activities"

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

def initialize_pinecone():
    # from pdb import set_trace
    # set_trace()
    # pinecone.init(
    # pc = Pinecone(api_key=PINECONE_API_KEY, host="https://activities-index-ku54fn2.svc.aped-4627-b74a.pinecone.io")
    pc = Pinecone(api_key=PINECONE_API_KEY,  environment="us-west-2-aws")
    if "activities-index" not in pc.list_indexes().names():
        pc.create_index(
            name="activities-index",
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws", 
                region="us-west-2"  
            )
        )
    index = pc.Index("activities-index")

    return index


def get_embedding(text):
    """
    Convert the user query to embedding vector using OpenAI.
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding
    return embedding


def query_pinecone(index, query_text, namespace, top_k=10):
    """
    Queries the Pinecone index using the embedding of the provided query text.
    Returns the raw query response, including the matched vectors.
    """
    # i'm pouring concrete 7 out of 10 parts
    query_embedding = get_embedding(query_text)
    query_response = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace
    )
    return query_response


def get_schedule_activity_summary(user_report, matches):
    """
    Formats the retrieved matches into a context string and uses GPT-4-o
    to generate a summary of the relevant schedule activities.
    """
    context = ""
    for i, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        context += f"Activity {i}:\n"
        context += f"  ID: {match.get('id')}\n"
        context += f"  Name: {metadata.get('name', 'N/A')}\n"
        # Optionally iterate over all metadata key-value pairs for additional context.
        for key, value in metadata.items():
            context += f"  {key}: {value}\n"
        context += "\n"

    prompt = f"""
        You are an assistant that analyzes user reports and matches them to schedule activities. 
        You have the following user report:

        \"\"\" 
        {user_report} 
        \"\"\"

        Below are several schedule activities, each with an ID, name, and additional metadata:

        \"\"\" 
        {context}
        \"\"\"

        1. For each activity, determine:
        - How relevant the activity is to the user report (fully relevant, partially relevant, or not relevant).
        - Why you made that assessment.

        2. Once you have made the assessments, create a final summary. 
        - In the summary, highlight the key details from the user report that connect with the most relevant activities.
        - If possible, mention any progress or updates you infer from the user report.

        Please structure your final answer in two parts:
        (A) Activity Relevance Evaluations
        (B) Concise Overall Summary

        Be clear, direct, and avoid extraneous commentary.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "You are a helpful assistant that summarizes schedule activities based on retrieval augmented context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    answer = response.choices[0].message.content
    return answer


def extract_progress(report, activity_name):
    """
    Uses GPT-4o to decide if the report includes quantitative progress status.
    If the report contains progress information, returns a float value.
    Otherwise, returns None.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    f"""
                    You are an assistant designed to extract numeric progress information for a specific activity 
                    from a user's report. You will receive two pieces of text: 
                    (1) The activity name 
                    (2) The user’s report describing possible progress.

                    Your job:
                    - Look for any mention of progress that can be interpreted as a number between 0 and 100.
                    - If it’s explicitly given (like “80% done” or “progress is 20”), extract that number.
                    - If it’s vague (like “almost done,” “halfway,” “a quarter done”), interpret it as a rough numeric percentage:
                    - “almost done” -> around 90%
                    - “halfway” -> 50
                    - “a quarter done” -> 25
                    (Use your best judgment if the text is ambiguous.)
                    - If there is no mention of progress at all, or it’s impossible to convert to a percentage, return 50.

                    Your output must be valid JSON in one line, with a single key 'progress', like:
                    {{"progress": 60.0}}
                    if the progress is 60%, or
                    {{"progress": 50.0}}
                    if you cannot extract or infer progress.

                    Follow these rules strictly:
                    1. Always output valid JSON.
                    2. Do not include other keys or text.
                    3. Make sure 'progress' is either a float (0.0 - 100.0) or null.
                    """
                )},
                {"role": "user", "content": f"Activity: {activity_name} \n Report: {report}"}
            ],
            temperature=0.0,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        reply = response.choices[0].message.content
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}, Response content: {response.choices[0].message.content}")
        return None

    try:
        # Parse the reply assuming it's a JSON string containing the progress key.
        data = json.loads(reply) if isinstance(reply, str) else reply
        return data.get("progress")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


def update_progress(object_id, new_progress):

    update_result = collection.update_one(
        {"task_id": object_id},
        {"$set": {"percentage_complete": new_progress}}
    )

    return update_result.modified_count > 0


def confirm_relevant_activities(matches):
    """
    Displays the list of matched activities and prompts the user
    to select which ones are relevant by entering their corresponding numbers.
    If no input is provided, all activities are assumed relevant.
    """
    print("\nMatched Activities:")
    for i, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        print(f"{i}. ID: {match['id']}, Name: {metadata.get('name', 'N/A')}")

    selection_input = input(
        "Enter the numbers of the relevant activities (comma separated), or press enter for all: ").strip()
    if not selection_input:
        # If the user presses enter without selection, use all matches.
        return matches
    try:
        selected_numbers = [int(num.strip()) for num in selection_input.split(",")]
        selected_matches = [matches[i - 1] for i in selected_numbers if 1 <= i <= len(matches)]
        return selected_matches
    except ValueError:
        print("Invalid input. Using all matched activities.")
        return matches


def assign_progress_to_activities(selected_matches, user_report):
    """
    For each relevant activity, attempt to extract progress from the user report.
    Then, allow the user to confirm or override that progress by providing a new value.
    Finally, update the progress to mongoDB.
    """
    for match in selected_matches:
        metadata = match.get("metadata", {})
        activity_name = metadata.get("name", "N/A")
        object_id = metadata.get("ObjectId", "N/A")
        # Attempt to extract progress from the report for this activity
        progress = extract_progress(user_report, activity_name)
        if progress is not None:
            print(f"\nDetected progress for '{activity_name}': {progress}")
            confirmation = input(f"Use detected progress for '{activity_name}'? (y/n): ").strip().lower()
            if confirmation != "y":
                progress_input = input(f"Enter progress for activity '{activity_name}' (e.g., 75): ")
                try:
                    progress = float(progress_input)
                except ValueError:
                    print("Invalid input. Skipping update for this activity.")
                    continue
        else:
            print(f"\n Nothing Detected progress for '{activity_name}'")
            progress_input = input(f"Enter progress for activity '{activity_name}' (e.g., 75): ")
            try:
                progress = float(progress_input)
            except ValueError:
                print("Invalid input. Skipping update for this activity.")
                continue

        # Update progress via the mongoDB
        update_progress(object_id, progress)


def main():
    file_name = "/u/dkwark/projects/construction_schedule_rag/src/output.json"
    project_name = os.path.splitext(os.path.basename(file_name))[0]
    print(f"Extracted project name: {project_name}")
    index = initialize_pinecone()
    # Specify the namespace (e.g., "projectX")
    namespace = project_name

    # Ask the user for a query
    user_report = input("Enter your report: ")

    # Retrieve the top-k results from the specified namespace
    results = query_pinecone(index, user_report, namespace, top_k=10)
    matches = results.get("matches", [])
    if not matches:
        print("No relevant activities found.")
        return
    else:
        print(get_schedule_activity_summary(user_report, matches))
        selected_matches = confirm_relevant_activities(matches)
        assign_progress_to_activities(selected_matches, user_report)


if __name__ == "__main__":
    main()