from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class TrackedEntity(BaseModel):
    """
    A signal from a tool to the Agent Loop to pin a database entity to the clipboard.
    This enables progressive disclosure (summary vs detail) and live-syncing.
    """

    item_type: Literal["task", "project", "journal"]
    item_id: int
    resolution: Literal["summary", "detail"] = "summary"
    ttl: int = 10


class ToolResult(BaseModel):
    status: Literal["success", "error"]

    # Tool results have three channels
    tool_response: str  # The main output or error message to send back to the agent
    results_to_add_to_clipboard: list[str] | None = None  # Any content here would be added to clipboard
    files_to_add_to_clipboard: list[Path] = []  # Any files here would be loaded to the clipboard
    entities_to_track: list[TrackedEntity] = []
