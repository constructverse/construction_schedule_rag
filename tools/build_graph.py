from collections.abc import Generator
from typing import Any
import sys
sys.path.append("src")

from dify_plugin import Tool
from build_graph import build_graph as do_build

class BuildGraphTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator:
        json_file = tool_parameters["json_file"]
        do_build(json_file)

        yield self.create_text_message(
            f"✅ Successfully built a graph from '{json_file}'."
        )
