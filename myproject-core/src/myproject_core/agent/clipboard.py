import zoneinfo
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


def _format_utc_for_display(value: str | datetime, timezone_str: str) -> str:
    """Convert a UTC datetime string to the given timezone for display."""
    if value is None:
        return ""
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        dt = value

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
    local = dt.astimezone(zoneinfo.ZoneInfo(timezone_str))
    return local.strftime("%Y-%m-%d %H:%M")


def _format_elapsed(last_turn_at: datetime, now: datetime, timezone_str: str) -> str:
    """Format elapsed time as a natural language string."""
    delta = now - last_turn_at
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return ""

    minutes = total_seconds // 60
    if minutes < 60:
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit} ago"

    hours = minutes // 60
    if hours < 24:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"

    days = hours // 24
    unit = "day" if days == 1 else "days"
    return f"{days} {unit} ago"


class AgentClipboardFile(BaseModel):
    # Path to the file
    file_path: Path
    # Content of the file (support textual content only for now)
    current_file_content: str
    previous_file_content: str | None = None
    # How many turns left until the file is removed from clipboard
    ttl: int
    # These flags make it easier to filter and parse
    is_new: bool = False  # Has the file just been added in this turn?
    is_edited: bool = False  # Has the file been modified in this turn?


class AgentClipboardToolResult(BaseModel):
    # Name of the tool
    tool_name: str
    # ID of the tool call returned by LLM backend
    tool_call_id: str
    # Results of tool call returned by the tools defined in myproject-tools
    tool_call_results: list[str]
    # How many turns left until the tool call result is removed from clipboard
    ttl: int


class AgentClipboardTodoItem(BaseModel):
    # Completion status of the task
    completed: bool = False
    # Textual description of the task
    task_desc: str


class AgentClipboardPinnedEntity(BaseModel):
    """Represents a database entity pinned to the clipboard."""

    item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"]
    item_id: int
    resolution: Literal["summary", "detail"]
    ttl: int

    # The actual database record converted to a dictionary.
    # This is updated every turn by the Agent loop (Live-Sync).
    data: dict[str, Any] = {}


class AgentClipboard(BaseModel):
    accessed_files: dict[str, AgentClipboardFile] = {}
    tool_results: dict[str, AgentClipboardToolResult] = {}
    todo_list: list[AgentClipboardTodoItem] = []
    pinned_entities: dict[str, AgentClipboardPinnedEntity] = {}
    memory_tag_hints: dict[str, int] = {}  # tag -> count of current memories
    user_profile_content: str | None = None  # Rendered user profile, never TTL-expires
    last_turn_at: datetime | None = None  # UTC timestamp of last user turn
    timezone: str = "UTC"

    def add_file_to_clipboard(self, file_path: Path, content: str, ttl: int):
        """Adds or updates a file in the clipboard."""
        if str(file_path) not in self.accessed_files.keys():
            # If the file does not exist in the clipboard, then add it
            new_file = AgentClipboardFile(
                file_path=file_path, current_file_content=content, is_new=True, ttl=ttl
            )
            self.accessed_files[str(file_path)] = new_file
        else:
            # If the file is already in the clipboard, add a new version of the content
            old_file = self.accessed_files[str(file_path)]
            old_file.previous_file_content = old_file.current_file_content
            old_file.current_file_content = content
            old_file.is_new = False
            old_file.is_edited = True

    def add_tool_result_to_clipboard(
        self, tool_name: str, tool_call_id: str, tool_call_results: list[str], ttl: int
    ):
        """Add results of tool call to the clipboard"""
        new_tool_result = AgentClipboardToolResult(
            tool_name=tool_name, tool_call_id=tool_call_id, tool_call_results=tool_call_results, ttl=ttl
        )
        self.tool_results[tool_call_id] = new_tool_result

    def remove_file_from_clipboard(self, file_path: Path) -> bool:
        """Remove a given file from clipboard
        Return False if file does not exist.
        """
        if str(file_path) in self.accessed_files:
            del self.accessed_files[str(file_path)]
            return True
        return False

    def pin_entity(
        self,
        item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"],
        item_id: int,
        resolution: Literal["summary", "detail"],
        ttl: int = 10,
    ):
        """Adds or updates a pinned entity (productivity or memory)."""
        key = f"{item_type}_{item_id}"
        if key in self.pinned_entities:
            # If it exists, update resolution and reset TTL
            self.pinned_entities[key].resolution = resolution
            self.pinned_entities[key].ttl = ttl
        else:
            self.pinned_entities[key] = AgentClipboardPinnedEntity(
                item_type=item_type,
                item_id=item_id,
                resolution=resolution,
                ttl=ttl,
            )

    def reduce_ttl(self):
        """Reduce ttl of every item stored in clipboard"""
        if self.accessed_files:
            for _, file in self.accessed_files.items():
                file.ttl = file.ttl - 1

        if self.tool_results:
            for _, tool_result in self.tool_results.items():
                tool_result.ttl = tool_result.ttl - 1

        if self.pinned_entities:
            for _, entity in self.pinned_entities.items():
                entity.ttl -= 1
                # DECAY: If an item gets old (e.g., <= 5 turns left), downgrade it to save tokens
                if entity.ttl <= 5 and entity.resolution == "detail":
                    entity.resolution = "summary"

    def remove_expired_items(self):
        """Remove expired files and tool call results"""
        # Reconstruct the dictionaries keeping only items with ttl > 0
        self.accessed_files = {key: file for key, file in self.accessed_files.items() if file.ttl > 0}
        self.tool_results = {key: result for key, result in self.tool_results.items() if result.ttl > 0}
        self.pinned_entities = {
            key: entity for key, entity in self.pinned_entities.items() if entity.ttl > 0
        }

    def commit(self):
        """Remove previous version of existing files from clipboard"""
        for clipboard_file in self.accessed_files.values():
            clipboard_file.is_new = False
            clipboard_file.is_edited = False
            clipboard_file.previous_file_content = None

    def render_to_markdown(self, shorten: bool = False, timezone: str = "UTC") -> str:
        """Converts clipboard contents into a structured Markdown string."""
        sections = []

        print(self)
        # Use the timezone property instead if exist
        if self.timezone:
            timezone = self.timezone

        # Render conversation timing if elapsed > 60 seconds
        if self.last_turn_at is not None:
            now = datetime.now(zoneinfo.ZoneInfo("UTC"))
            elapsed = _format_elapsed(self.last_turn_at, now, timezone)
            if elapsed:
                last_local = _format_utc_for_display(self.last_turn_at, timezone)
                timing_section = "### CONVERSATION TIMING\n"
                timing_section += f"The last exchange was at {last_local} ({elapsed}).\n"
                sections.append(timing_section)

        # Render Todo List
        if self.todo_list:
            todo_section = "### AGENT INTERNAL TODO LIST\n"
            todo_section = "This list is your own to-do list to keep track of your tasks towards achieving your current goals.\n\n"
            for item in self.todo_list:
                status = "[x]" if item.completed else "[ ]"
                todo_section += f"{status} {item.task_desc}\n"
            sections.append(todo_section)

        # Render pinned productivity items
        if self.pinned_entities:
            prod_section = "### USER PRODUCTIVITY SYSTEM (LIVE SYNCED)\n"
            prod_section += "These items are pinned to your clipboard and reflect their real-time state in the database.\n\n"

            # Group by type for cleaner reading
            tasks = [e for e in self.pinned_entities.values() if e.item_type == "task" and e.data]
            projects = [e for e in self.pinned_entities.values() if e.item_type == "project" and e.data]
            journals = [e for e in self.pinned_entities.values() if e.item_type == "journal" and e.data]

            if tasks:
                prod_section += "#### TRACKED TASKS\n"
                for t in tasks:
                    d = t.data
                    prod_section += f"- **[ID: {t.item_id}]** {d.get('title', 'Unknown')} | Status: `{d.get('status', 'Unknown')}`"
                    if d.get("assigned_date"):
                        prod_section += f" | Date: {d.get('assigned_date')}"
                    if d.get("hard_deadline"):
                        deadline = _format_utc_for_display(d["hard_deadline"], timezone)
                        prod_section += f" | Deadline: {deadline}"
                    if d.get("scheduled_start"):
                        scheduled = _format_utc_for_display(d["scheduled_start"], timezone)
                        prod_section += f" | Scheduled Start Date: {scheduled}"
                    prod_section += "\n"

                    if t.resolution == "detail" and not shorten:
                        prod_section += f"  - **Description:** {d.get('description') or 'None'}\n"
                        prod_section += f"  - **Project Links:** {d.get('project_ids', [])}\n"
                prod_section += "\n"

            if projects:
                prod_section += "#### TRACKED PROJECTS\n"
                for p in projects:
                    d = p.data
                    prod_section += f"- **[ID: {p.item_id}]** {d.get('name', 'Unknown')} | Status: `{d.get('status', 'Unknown')}`\n"
                    if p.resolution == "detail" and not shorten:
                        prod_section += f"  - **Description:** {d.get('description') or 'None'}\n"
                        prod_section += f"  - **Deadline:** {d.get('deadline') or 'None'}\n"
                prod_section += "\n"

            if journals:
                prod_section += "#### TRACKED JOURNALS\n"
                for j in journals:
                    d = j.data
                    prod_section += f"- **[ID: {j.item_id}]** {d.get('title') or 'Untitled'} | Type: `{d.get('entry_type', 'Unknown')}` | Ref Date: {d.get('reference_date', 'Unknown')}\n"
                    if j.resolution == "detail" and not shorten:
                        prod_section += f"  - **Content:**\n```markdown\n{d.get('content', '')}\n```\n"
                prod_section += "\n"

            memory_events = [e for e in self.pinned_entities.values() if e.item_type == "memory_event"]
            memory_topics = [e for e in self.pinned_entities.values() if e.item_type == "memory_topic"]

            if memory_events or memory_topics:
                prod_section += "#### TRACKED MEMORIES\n"
                if memory_events:
                    prod_section += "##### MEMORY EVENTS\n"
                    for m in memory_events:
                        d = m.data
                        # Basic info available without sync
                        subject = d.get("subject") or "Untitled Event" if d else f"Event ID {m.item_id}"
                        importance = d.get("importance", 3) if d else "?"
                        event_time = d.get("event_time", "") if d else ""
                        if event_time:
                            if hasattr(event_time, "isoformat"):
                                event_time = event_time.isoformat()
                            prod_section += f"- **[ID: {m.item_id}]** {subject} | Importance: `{importance}/5` | Event Time: {event_time}\n"
                        else:
                            prod_section += (
                                f"- **[ID: {m.item_id}]** {subject} | Importance: `{importance}/5`\n"
                            )
                        # Detail requires data
                        if m.resolution == "detail" and not shorten and d:
                            prod_section += f"  - **Content:** {d.get('content', 'None')}\n"
                            tags = d.get("tags", [])
                            prod_section += f"  - **Tags:** {', '.join(tags) if tags else 'None'}\n"
                            prod_section += f"  - **Source:** {d.get('source', 'Unknown')}\n"
                    prod_section += "\n"
                if memory_topics:
                    prod_section += "##### MEMORY TOPICS\n"
                    for m in memory_topics:
                        d = m.data
                        # Basic info available without sync
                        subject = d.get("subject") or "Untitled Topic" if d else f"Topic ID {m.item_id}"
                        importance = d.get("importance", 3) if d else "?"
                        updated_at = d.get("updated_at", "") if d else ""
                        if updated_at:
                            if hasattr(updated_at, "isoformat"):
                                updated_at = updated_at.isoformat()
                            prod_section += f"- **[ID: {m.item_id}]** {subject} | Importance: `{importance}/5` | Updated: {updated_at}\n"
                        else:
                            prod_section += (
                                f"- **[ID: {m.item_id}]** {subject} | Importance: `{importance}/5`\n"
                            )
                        # Detail requires data
                        if m.resolution == "detail" and not shorten and d:
                            prod_section += f"  - **Content:** {d.get('content', 'None')}\n"
                            tags = d.get("tags", [])
                            prod_section += f"  - **Tags:** {', '.join(tags) if tags else 'None'}\n"
                            prod_section += f"  - **Source:** {d.get('source', 'Unknown')}\n"
                            superseded_by = d.get("superseded_by_id")
                            if superseded_by:
                                prod_section += f"  - **Superseded by:** ID {superseded_by}\n"
                            supersedes = d.get("supersedes_ids", [])
                            if supersedes:
                                prod_section += (
                                    f"  - **Supersedes:** IDs {', '.join(str(x) for x in supersedes)}\n"
                                )
                    prod_section += "\n"

            sections.append(prod_section)

        # Render Files
        if self.accessed_files:
            new_files = [file for file in self.accessed_files.values() if file.is_new]
            edited_files = [file for file in self.accessed_files.values() if file.is_edited]
            file_section = "### ACCESSED FILES\n\n"
            file_section += "The following files have been read, written, or edited **by you** so far.\n"
            file_section += "\n\n"

            if new_files:
                file_section += (
                    f"You have read and added **{len(new_files)} files** to the clipboard recently\n"
                )
                file_section += "List of newly added files:\n"
                for new_file in new_files:
                    file_section += f"- `{new_file.file_path}`\n"
                file_section += "\n\n"

            if edited_files:
                file_section += f"You have edited **{len(edited_files)} files** recently:\n"
                file_section += "List of recently edited files:\n"
                for edited_file in edited_files:
                    file_section += f"- `{edited_file.file_path}`\n"
                file_section += "\n\n"

            for _, file in self.accessed_files.items():
                file_section += f"#### File: {file.file_path}\n"
                if file.is_new:
                    file_section += "**Status: Recently Added**\n"
                if file.is_edited:
                    file_section += "**Status: Recently Modified**\n"

                if not shorten:
                    file_section += f"**Current File Content:**\n```\n{file.current_file_content}\n```\n\n"
                    if file.previous_file_content:
                        file_section += (
                            f"**Previous File Content:**\n```\n{file.previous_file_content}\n```\n"
                        )
                else:
                    file_section += (
                        f"**Current File Content:**\n```\n{file.current_file_content[0:50]}...\n```\n"
                    )
                    if file.previous_file_content:
                        file_section += (
                            f"**Previous File Content:**\n```\n{file.previous_file_content[0:50]}...\n```\n"
                        )
                file_section += "\n\n-----\n\n"
            sections.append(file_section)

        # Render tool results
        if self.tool_results:
            tool_section = "### TOOL CALL RESULTS\n\n"
            for _, tool_result in self.tool_results.items():
                tool_section += f"#### Tool Call ID: {tool_result.tool_call_id}\n"
                tool_section += f"Tool: {tool_result.tool_name}\n"
                for res in tool_result.tool_call_results:
                    if not shorten:
                        tool_section += f"```\n{res}\n```\n"
                    else:
                        tool_section += f"```\n{res[:50]}...\n```\n"

                    tool_section += "\n\n-----\n\n"
            sections.append(tool_section)

        # Render memory tag hints
        if self.memory_tag_hints:
            tag_section = "### MEMORY TAGS\n\n"
            tag_section += "Available semantic tags across all memories:\n"
            # Sort alphabetically for stable, predictable output
            for tag in sorted(self.memory_tag_hints):
                count = self.memory_tag_hints[tag]
                tag_section += f"- {tag} ({count})\n"
            sections.append(tag_section)

        # Render user profile
        if self.user_profile_content is not None:
            profile_section = "### USER PROFILE\n\n```\n" + self.user_profile_content + "\n```\n"
            sections.append(profile_section)
        else:
            profile_section = '### USER PROFILE\n\nYou don\'t have a user profile yet. When the time feels right — e.g., the user says hello, asks what you can do, or seems open to chatting — start an onboarding process to learn more about user to create a profile so that you can interact with user better.\n\nWhen you\'re ready to record what you learn, use:\nremember_this(memory_type="topic", subject="user-profile", tags=["user-profile"], content="...")\n'
            sections.append(profile_section)

        if not sections:
            return "Clipboard is currently empty."

        return "\n\n".join(sections)

    def get_accessed_files_paths(self) -> list[Path]:
        """Return a list of paths of all accessed files"""
        str_paths: list[str] = list(self.accessed_files.keys())
        return [Path(str_path) for str_path in str_paths]
