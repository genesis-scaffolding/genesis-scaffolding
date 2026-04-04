from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

from sqlmodel import Session

from myproject_core.productivity.models import Task

from .memory import service as memory_service
from .productivity import service as prod_service
from .schemas import AgentClipboard


class AgentMemory:
    def __init__(
        self,
        messages: list[Any] | None = None,
        agent_clipboard: AgentClipboard | None = None,
    ) -> None:
        self.messages = messages or []
        self.agent_clipboard = agent_clipboard or AgentClipboard()

    def append_memory(self, message: Any):
        self.messages.append(message)

    def get_messages(self) -> list[Any]:
        """Returns the raw message history."""
        return self.messages

    def reset_memory(self):
        self.messages = []
        self.agent_clipboard = AgentClipboard()

    def remove_deleted_files(self, working_dir: Path = Path()) -> list[Path]:
        """Automatically remove deleted files from the clipboard

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
        """Formats the clipboard as a system message.
        This is ephemeral and should not be stored in self.messages.
        """
        now = datetime.now(ZoneInfo(timezone))
        content = (
            "## CURRENT CLIPBOARD\n"
            f"{self.agent_clipboard.render_to_markdown(shorten=shorten, timezone=timezone)}\n\n\n=====\n"
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
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_call_results=results,
        )

    def remove_file_from_clipboard(self, file_path: Path) -> bool:
        """Remove a file from clipboard
        Return False if failed to remove file
        """
        try:
            if self.agent_clipboard.remove_file_from_clipboard(file_path):
                return True
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

    def pin_entity(
        self,
        item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"],
        item_id: int,
        resolution: Literal["summary", "detail"],
        ttl: int = 10,
    ):
        """Delegates pinning an entity to the clipboard schema."""
        self.agent_clipboard.pin_entity(item_type, item_id, resolution, ttl)

    def sync_entities(self, session: Session, db_type: Literal["productivity", "memory"] | None = None):
        """Iterates over all pinned entities in the clipboard, fetches their
        latest state from the appropriate database, and converts them to dictionaries for the LLM.
        If an entity was deleted from the database, it removes it from the clipboard.

        Args:
            session: The database session to use
            db_type: Which database to sync. If None, syncs all entity types.
                     Use "productivity" for user_db sessions, "memory" for memory_db sessions.
        """
        # We iterate over a list of keys so we can safely delete from the dict if needed
        keys_to_sync = list(self.agent_clipboard.pinned_entities.keys())

        for key in keys_to_sync:
            entity = self.agent_clipboard.pinned_entities[key]
            db_item = None

            # Determine which DB this entity belongs to and check if we should process it
            if entity.item_type == "task":
                if db_type and db_type != "productivity":
                    continue
                db_item = prod_service.get_task(session, entity.item_id)
            elif entity.item_type == "project":
                if db_type and db_type != "productivity":
                    continue
                db_item = prod_service.get_project(session, entity.item_id)
            elif entity.item_type == "journal":
                if db_type and db_type != "productivity":
                    continue
                db_item = prod_service.get_journal(session, entity.item_id)
            elif entity.item_type == "memory_event":
                if db_type and db_type != "memory":
                    continue
                db_item = memory_service.get_event_log(session, entity.item_id)
            elif entity.item_type == "memory_topic":
                if db_type and db_type != "memory":
                    continue
                db_item = memory_service.get_topical_memory(session, entity.item_id)
            else:
                # Unknown entity type, skip
                continue

            # Update or Remove
            if db_item is None:
                # The item was deleted from the DB (e.g., by the user in the UI)
                del self.agent_clipboard.pinned_entities[key]
            else:
                # Serialize the SQLModel to a dict.
                # Mode="json" ensures dates/datetimes are converted to strings safely
                data = db_item.model_dump(mode="json")

                # Special handling for Task's computed property "project_ids"
                if entity.item_type == "task":
                    db_item = cast("Task", db_item)
                    data["project_ids"] = db_item.project_ids

                entity.data = data

    def sync_memory_tag_hints(self, session: Session):
        """Fetch current tag counts from the memory DB and update the clipboard."""
        counts = memory_service.get_memory_tag_counts(session)
        self.agent_clipboard.memory_tag_hints = counts

    def sync_user_profile(self, session: Session):
        """Fetch the user profile topical memory and cache its content in the clipboard.

        Uses get_user_profile() which finds entries tagged "user-profile", returning
        the most recently updated active entry. If no profile exists, sets
        user_profile_content to None — the clipboard will render the onboarding nudge
        instead.
        """
        from .memory import service as memory_service

        profile = memory_service.get_user_profile(session)
        self.agent_clipboard.user_profile_content = profile.content if profile else None

    def estimate_total_tokens(self) -> int:
        """Estimates the total token count of history + current clipboard.
        Uses a 4-char-per-token heuristic.
        """
        # 1. Calculate History length
        history_text = "".join([m["content"] for m in self.messages])

        # 2. Calculate Clipboard length (as it will be rendered)
        clipboard_text = self.agent_clipboard.render_to_markdown()

        total_chars = len(history_text) + len(clipboard_text)
        return total_chars // 4
