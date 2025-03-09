from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
import sys
sys.path.append("src")

# Import your function from the src/ module
from xml_parser import convert_xml_to_json as convert_fn

class ConvertXmlToJsonTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator:
        xml_file = tool_parameters["xml_file"]
        json_file = tool_parameters["json_file"]

        # Call your logic from src/xml_parser.py
        convert_fn(xml_file, json_file)

        yield self.create_text_message(
            f"✅ Successfully converted '{xml_file}' → '{json_file}'."
        )
