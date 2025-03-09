from collections.abc import Generator
from typing import Any
import sys
sys.path.append("src")
import json

from dify_plugin import Tool
from filter_by_date import filter_activities_by_date

class FilterActivitiesByDateTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator:
        json_file = tool_parameters["json_file"]
        target_date = tool_parameters["target_date"]
        output_file = tool_parameters["output_file"]

        filtered = filter_activities_by_date(json_file, target_date)
        if filtered:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=4)

            yield self.create_text_message(
                f"✅ Found {len(filtered)} activities for {target_date}. Saved to '{output_file}'."
            )
        else:
            yield self.create_text_message(
                f"❌ No activities found on {target_date}."
            )
