from crewai_tools import XMLSearchTool
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

tool = XMLSearchTool(config=dict(
        llm=dict(
            provider="openai",  # Specify your LLM provider (e.g., 'openai', 'anthropic')
            config=dict(
                model="gpt-4",  # Model to use
                api_key=api_key,  # Add your API key here
            ),
        )
    ))

# Load the XML file
results = tool.process(xml_path="TERMPROJ-10.xml", query="Activity")
print("Search Results:", results)

# Output the results: <ActivityName><PredecessorName><SuccessorName><Duration>


# Clean up the output 

