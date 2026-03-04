from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .configs import get_config
from .schemas import AgentClipboard


class AgentMemory:
    def __init__(
        self, messages: list[Any] | None = None, agent_clipboard: AgentClipboard | None = None
    ) -> None:
        self.messages = messages if messages else []
        self.agent_clipboard = agent_clipboard if agent_clipboard else AgentClipboard()

    def append_memory(self, message: Any):
        self.messages.append(message)

    def get_messages(self) -> list[Any]:
        """Returns the raw message history."""
        return self.messages

    def reset_memory(self):
        self.messages = []
        self.agent_clipboard = AgentClipboard()

    def remove_deleted_files(self, working_dir: Path = Path(".")) -> list[Path]:
        """
        Automatically remove deleted files from the clipboard

        working_dir is important for the server use where files are located using relative paths rather than absolute paths
        """
        accessed_files_paths = self.agent_clipboard.get_accessed_files_paths()
        files_to_remove = [
            file_path for file_path in accessed_files_paths if not (working_dir / file_path).exists()
        ]
        files_removed = []
        for file_path in files_to_remove:
            if self.agent_clipboard.remove_file_from_clipboard(file_path):
                files_removed.append(file_path)
        return files_removed

    def forget(self):
        self.agent_clipboard.reduce_ttl()
        self.agent_clipboard.remove_expired_items()
        self.agent_clipboard.commit()

    def get_clipboard_message(self, shorten: bool = False, timezone: str = "UTC") -> dict[str, str]:
        """
        Formats the clipboard as a system message.
        This is ephemeral and should not be stored in self.messages.
        """
        now = datetime.now(ZoneInfo(timezone))
        content = (
            "## CURRENT CLIPBOARD\n"
            f"{self.agent_clipboard.render_to_markdown(shorten=shorten)}\n\n\n=====\n"
            "## CURRENT DATE TIME\n"
            f"{now.strftime('%Y-%m-%d %H:%M:%S %Z %z')}\n\n====="
        )
        return {"role": "system", "content": content}

    def add_file_to_clipboard(self, file_path: Path, content: str):
        """Adds or updates a file in the clipboard."""
        self.agent_clipboard.add_file_to_clipboard(file_path=file_path, content=content)

    def add_tool_results_to_clipboard(self, tool_name: str, tool_call_id: str, results: list[str]):
        """Adds tool results to clipboard"""
        self.agent_clipboard.add_tool_result_to_clipboard(
            tool_name=tool_name, tool_call_id=tool_call_id, tool_call_results=results
        )

    def remove_file_from_clipboard(self, file_path: Path) -> bool:
        """
        Remove a file from clipboard
        Return False if failed to remove file
        """
        try:
            if self.agent_clipboard.remove_file_from_clipboard(file_path):
                return True
            else:
                return False
        except Exception:
            return False

    def remove_dir_from_clipboard(self, dir_path: Path) -> list[Path]:
        accessed_files_paths = self.agent_clipboard.get_accessed_files_paths()
        files_to_remove = [
            file_path for file_path in accessed_files_paths if file_path.is_relative_to(dir_path)
        ]
        files_removed = []
        for file_path in files_to_remove:
            if self.agent_clipboard.remove_file_from_clipboard(file_path):
                files_removed.append(file_path)
        return files_removed

    def estimate_total_tokens(self) -> int:
        """
        Estimates the total token count of history + current clipboard.
        Uses a 4-char-per-token heuristic.
        """
        # 1. Calculate History length
        history_text = "".join([m["content"] for m in self.messages])

        # 2. Calculate Clipboard length (as it will be rendered)
        clipboard_text = self.agent_clipboard.render_to_markdown()

        total_chars = len(history_text) + len(clipboard_text)
        return total_chars // 4
