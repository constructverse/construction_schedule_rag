from collections.abc import Generator
from typing import Any
import sys
sys.path.append("src")

from dify_plugin import Tool
from visualized_filtered_activities import visualize_activities

class VisualizeActivitiesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator:
        json_file = tool_parameters["json_file"]
        date_label = tool_parameters.get("date", "")

        visualize_activities(json_file, date_label)

        yield self.create_text_message(
            f"✅ Visualization generated for file '{json_file}' (label: {date_label})."
        )
