from pathlib import Path
from typing import Any

from .base import BaseTool
from .schema import ToolResult


class MockTestTool(BaseTool):
    name = "test_tool"
    description = "A tool for testing the agent's ability to handle success and failure."
    parameters = {
        "type": "object",
        "properties": {"input_text": {"type": "string"}, "should_fail": {"type": "boolean"}},
    }

    async def run(
        self, working_directory: Path, input_text: str, should_fail: bool = False, **kwargs: Any,
    ) -> ToolResult:
        if should_fail:
            # Test exception catching
            raise Exception(f"Simulated crash with input: {input_text}")

        return ToolResult(
            tool_response="Processed input text successfully and added to the clipboard",
            status="success",
            results_to_add_to_clipboard=[f"{input_text}"],
        )
