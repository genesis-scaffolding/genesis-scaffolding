"""Memory tools for creating, searching, and managing persistent agent memories."""

from datetime import UTC, datetime
from typing import Any, Literal, cast

from genesis_core.persistent_memory import service as memory_service
from genesis_core.persistent_memory.db import get_memory_session
from genesis_core.persistent_memory.models import EventLog, MemorySource, TopicalMemory

from .base import BaseTool
from .schema import ToolResult, TrackedEntity


def _memory_to_dict(
    memory: EventLog | TopicalMemory, memory_type: Literal["event", "topic"]
) -> dict[str, Any]:
    """Convert a memory model to a dictionary for clipboard tracking."""
    return {
        "id": memory.id,
        "type": memory_type,
        "subject": memory.subject,
        "content": memory.content,
        "tags": memory.tags,
        "importance": memory.importance,
        "source": memory.source.value if isinstance(memory.source, MemorySource) else memory.source,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def _format_memory_for_response(
    memory: EventLog | TopicalMemory, memory_type: Literal["event", "topic"]
) -> str:
    """Format a memory for the tool response text."""
    type_label = "Event" if memory_type == "event" else "Topic"
    subject_line = memory.subject if memory.subject else f"Untitled {type_label}"
    time_info = ""
    if memory_type == "event" and isinstance(memory, EventLog):
        time_info = f" (at {memory.event_time.isoformat()})"

    response = f"[{type_label}] {subject_line}{time_info}\n"
    response += f"ID: {memory.id}\n"
    response += f"Content: {memory.content}\n"
    if memory.tags:
        response += f"Tags: {', '.join(memory.tags)}\n"
    response += f"Importance: {memory.importance}/5\n"
    response += (
        f"Source: {memory.source.value if isinstance(memory.source, MemorySource) else memory.source}\n"
    )
    if isinstance(memory, TopicalMemory) and memory.superseded_by_id:
        response += f"Superseded by: ID {memory.superseded_by_id}\n"
    if isinstance(memory, TopicalMemory) and memory.supersedes_ids:
        response += f"Supersedes: IDs {', '.join(str(x) for x in memory.supersedes_ids)}\n"
    response += f"Created: {memory.created_at}\n"
    response += f"Updated: {memory.updated_at}\n"
    return response


def _make_memory_entity(
    memory_type_literal: Literal["memory_event", "memory_topic"],
    memory_id: int,
    resolution: Literal["summary", "detail"] = "summary",
    ttl: int = 10,
) -> TrackedEntity:
    """Helper to create a TrackedEntity with proper typing."""
    return TrackedEntity(
        item_type=memory_type_literal,
        item_id=memory_id,
        resolution=resolution,
        ttl=ttl,
    )


class RememberThisTool(BaseTool):
    """Store a new memory about the user or their context."""

    name = "remember_this"
    description = (
        "Stores a new memory about the user or their context. "
        "Use memory_type='event' for discrete moments in time (append-only). "
        "Use memory_type='topic' for knowledge that can be revised later (supersedes old entries). "
        "Tags help with later retrieval. Importance is 1-5 (3=default). "
        "For events, event_time is required (ISO8601 or YYYY-MM-DD). "
        "Returns the created memory ID for later reference."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The memory content to store."},
            "memory_type": {
                "type": "string",
                "enum": ["event", "topic"],
                "description": "'event' for discrete moments (append-only), 'topic' for revisable knowledge.",
            },
            "subject": {"type": "string", "description": "Optional display label for the memory."},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags to help with retrieval.",
            },
            "event_time": {
                "type": "string",
                "description": "Required for events. When the event happened. ISO8601 or YYYY-MM-DD.",
            },
            "importance": {
                "type": "integer",
                "description": "Importance 1-5 (3=default). Higher = more important.",
            },
            "related_memory_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional IDs of related memories to link.",
            },
        },
        "required": ["content", "memory_type"],
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        content = kwargs.get("content")
        memory_type = kwargs.get("memory_type")
        if not content or not memory_type:
            return ToolResult(status="error", tool_response="content and memory_type are required.")

        subject = kwargs.get("subject")
        tags: list[str] = kwargs.get("tags", [])
        importance: int = kwargs.get("importance", 3)
        related_memory_ids: list[int] = kwargs.get("related_memory_ids", [])

        event_time: datetime | None = None
        if memory_type == "event":
            event_time_str = kwargs.get("event_time")
            if not event_time_str:
                return ToolResult(
                    status="error", tool_response="event_time is required for memory_type='event'."
                )
            try:
                # Try parsing ISO format first
                if "T" in event_time_str:
                    event_time = datetime.fromisoformat(event_time_str)
                else:
                    # Try date format YYYY-MM-DD
                    from datetime import date

                    d = date.fromisoformat(event_time_str)
                    event_time = datetime.combine(d, datetime.min.time()).replace(tzinfo=UTC)
            except ValueError:
                return ToolResult(
                    status="error",
                    tool_response=f"Invalid event_time format: {event_time_str}. Use ISO8601 or YYYY-MM-DD.",
                )

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                data: dict[str, Any] = {
                    "content": content,
                    "subject": subject,
                    "tags": tags,
                    "importance": importance,
                    "source": MemorySource.AGENT_TOOL,
                    "related_memory_ids": related_memory_ids,
                }
                if memory_type == "event":
                    data["event_time"] = event_time
                    entry = memory_service.create_event_log(session, data)
                    entity_type: Literal["memory_event", "memory_topic"] = "memory_event"
                else:
                    entry = memory_service.create_topical_memory(session, data)
                    entity_type = "memory_topic"

                entry_id = entry.id
                if entry_id is None:
                    return ToolResult(status="error", tool_response="Failed to retrieve created memory ID.")

                return ToolResult(
                    status="success",
                    tool_response=f"Memory stored successfully. ID: {entry_id}",
                    entities_to_track=[
                        _make_memory_entity(entity_type, entry_id, "summary", 10),
                    ],
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to store memory: {e}")

        # This should never happen since the generator always yields at least once
        return ToolResult(status="error", tool_response="Memory session unavailable.")


class SearchMemoriesTool(BaseTool):
    """Search memories by keyword across subject and content."""

    name = "search_memories"
    description = (
        "Search across all memories by keyword. Searches subject and content fields. "
        "Returns matching events and topics (current only, not superseded). "
        "Use memory_type to filter to 'event', 'topic', or 'all' (default)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search keyword/phrase."},
            "memory_type": {
                "type": "string",
                "enum": ["event", "topic", "all"],
                "description": "Filter by memory type. Default is 'all'.",
            },
            "limit": {"type": "integer", "description": "Max results per type. Default is 20."},
        },
        "required": ["query"],
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        query: str | None = kwargs.get("query")
        memory_type: str = kwargs.get("memory_type", "all")
        limit: int = kwargs.get("limit", 20)

        if not query:
            return ToolResult(status="error", tool_response="query is required.")

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                actual_memory_type = cast(Literal["event", "topic", "all"], memory_type)
                results = memory_service.search_memories(session, query, actual_memory_type, limit)

                event_results = results["events"]
                topic_results = results["topics"]

                if not event_results and not topic_results:
                    return ToolResult(
                        status="success", tool_response=f"No memories found matching '{query}'."
                    )

                entities: list[TrackedEntity] = []
                for m in event_results:
                    if m.id is not None:
                        entities.append(_make_memory_entity("memory_event", m.id, "summary", 5))
                for m in topic_results:
                    if m.id is not None:
                        entities.append(_make_memory_entity("memory_topic", m.id, "summary", 5))

                return ToolResult(
                    status="success",
                    tool_response=f"Found {len(event_results)} events and {len(topic_results)} topics matching '{query}'. Results pinned to clipboard.",
                    entities_to_track=entities,
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e}")

        return ToolResult(status="error", tool_response="Memory session unavailable.")


class ListMemoriesTool(BaseTool):
    """List memories with optional filters."""

    name = "list_memories"
    description = (
        "List memories with optional filters. "
        "Use memory_type to list 'event', 'topic', or 'all' (default). "
        "Topics by default exclude superseded entries. "
        "Sort by created_at, updated_at, event_time, or importance."
    )
    parameters = {
        "type": "object",
        "properties": {
            "memory_type": {
                "type": "string",
                "enum": ["event", "topic", "all"],
                "description": "Type of memories to list. Default is 'all'.",
            },
            "tag": {"type": "string", "description": "Filter by tag."},
            "importance": {"type": "integer", "description": "Filter by importance (1-5)."},
            "source": {
                "type": "string",
                "enum": ["agent_tool", "dream_workflow", "user_manual"],
                "description": "Filter by source.",
            },
            "include_superseded": {
                "type": "boolean",
                "description": "For topics only: include superseded entries. Default is False.",
            },
            "sort_by": {
                "type": "string",
                "enum": ["created_at", "updated_at", "event_time", "importance"],
                "description": "Sort field. Default varies by type.",
            },
            "order": {
                "type": "string",
                "enum": ["asc", "desc"],
                "description": "Sort order. Default is 'desc'.",
            },
            "limit": {"type": "integer", "description": "Max results. Default is 50."},
            "offset": {"type": "integer", "description": "Pagination offset. Default is 0."},
        },
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        memory_type: str = kwargs.get("memory_type", "all")
        tag: str | None = kwargs.get("tag")
        importance: int | None = kwargs.get("importance")
        source_str: str | None = kwargs.get("source")
        source = MemorySource(source_str) if source_str else None
        include_superseded: bool = kwargs.get("include_superseded", False)
        sort_by: str = kwargs.get("sort_by", "event_time" if memory_type == "event" else "updated_at")
        order: str = kwargs.get("order", "desc")
        limit: int = kwargs.get("limit", 50)
        offset: int = kwargs.get("offset", 0)

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                events: list[EventLog] = []
                topics: list[TopicalMemory] = []

                # Cast sort_by based on memory_type default
                if memory_type in ("all", "event"):
                    actual_sort_by = cast(Literal["event_time", "created_at", "importance"], sort_by)
                    actual_order = cast(Literal["asc", "desc"], order)
                    events = list(
                        memory_service.list_event_logs(
                            session,
                            tag=tag,
                            importance=importance,
                            source=source,
                            sort_by=actual_sort_by,
                            order=actual_order,
                            limit=limit,
                            offset=offset,
                        )
                    )

                if memory_type in ("all", "topic"):
                    actual_sort_by = cast(Literal["created_at", "updated_at", "importance"], sort_by)
                    actual_order = cast(Literal["asc", "desc"], order)
                    topics = list(
                        memory_service.list_topical_memories(
                            session,
                            superseded=include_superseded,
                            tag=tag,
                            importance=importance,
                            source=source,
                            sort_by=actual_sort_by,
                            order=actual_order,
                            limit=limit,
                            offset=offset,
                        )
                    )

                if not events and not topics:
                    return ToolResult(
                        status="success", tool_response="No memories found matching the criteria."
                    )

                entities: list[TrackedEntity] = []

                if events:
                    for m in events:
                        if m.id is not None:
                            entities.append(_make_memory_entity("memory_event", m.id, "summary", 5))

                if topics:
                    for m in topics:
                        if m.id is not None:
                            entities.append(_make_memory_entity("memory_topic", m.id, "summary", 5))

                count_msg = []
                if events:
                    count_msg.append(f"{len(events)} events")
                if topics:
                    count_msg.append(f"{len(topics)} topics")
                return ToolResult(
                    status="success",
                    tool_response=f"Listed {', '.join(count_msg)}. Results pinned to clipboard.",
                    entities_to_track=entities,
                )
        except Exception as e:
            import traceback

            return ToolResult(
                status="error",
                tool_response=f"Failed to list memories: {type(e).__name__}: {e}\n{traceback.format_exc()}",
            )

        return ToolResult(status="error", tool_response="Memory session unavailable.")


class GetMemoryTool(BaseTool):
    """Retrieve a specific memory by ID."""

    name = "get_memory"
    description = (
        "Retrieve the full details of a specific memory by its ID. "
        "Use this to get the complete content of a memory after using search or list. "
        "The memory will be pinned to your clipboard with detail resolution."
    )
    parameters = {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer", "description": "The ID of the memory to retrieve."},
            "memory_type": {
                "type": "string",
                "enum": ["event", "topic"],
                "description": "The type of memory ('event' or 'topic').",
            },
        },
        "required": ["memory_id", "memory_type"],
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        memory_id: int | None = kwargs.get("memory_id")
        memory_type: str | None = kwargs.get("memory_type")

        if not memory_id or not memory_type:
            return ToolResult(status="error", tool_response="memory_id and memory_type are required.")

        if memory_type not in ("event", "topic"):
            return ToolResult(status="error", tool_response="memory_type must be 'event' or 'topic'.")

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                if memory_type == "event":
                    entry = memory_service.get_event_log(session, memory_id)
                else:
                    entry = memory_service.get_topical_memory(session, memory_id)

                if not entry:
                    return ToolResult(
                        status="error", tool_response=f"Memory {memory_type} with ID {memory_id} not found."
                    )

                # For topics, get revision chain info for the notification
                chain_info = ""
                if isinstance(entry, TopicalMemory):
                    chain = memory_service.get_revision_chain(session, memory_id)
                    if len(chain) > 1:
                        chain_info = f" (revision chain: {len(chain)} entries)"

                entry_id = entry.id
                if entry_id is None:
                    return ToolResult(status="error", tool_response="Memory has no ID.")

                entity_type: Literal["memory_event", "memory_topic"] = (
                    "memory_event" if memory_type == "event" else "memory_topic"
                )

                return ToolResult(
                    status="success",
                    tool_response=f"Retrieved {memory_type} memory ID {entry_id}{chain_info}. Pinned to clipboard.",
                    entities_to_track=[
                        _make_memory_entity(entity_type, entry_id, "detail", 10),
                    ],
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to retrieve memory: {e}")

        return ToolResult(status="error", tool_response="Memory session unavailable.")


class UpdateMemoryTool(BaseTool):
    """Update a topical memory. This creates a new revision, preserving history via supersession."""

    name = "update_memory"
    description = (
        "Update a topical memory's content. This DOES NOT overwrite in-place — "
        "instead it creates a new revision and marks the old one as superseded. "
        "This preserves the full revision history. "
        "Use get_memory to see the revision chain. "
        "NOTE: For events, use delete + remember_this instead (events are append-only)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer", "description": "The ID of the topic memory to update."},
            "content": {"type": "string", "description": "The new memory content."},
            "subject": {"type": "string", "description": "Optional new subject/display label."},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional new tags list (replaces existing).",
            },
            "importance": {"type": "integer", "description": "Optional new importance (1-5)."},
        },
        "required": ["memory_id", "content"],
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        memory_id: int | None = kwargs.get("memory_id")
        content: str | None = kwargs.get("content")

        if not memory_id or not content:
            return ToolResult(status="error", tool_response="memory_id and content are required.")

        subject: str | None = kwargs.get("subject")
        tags: list[str] | None = kwargs.get("tags")
        kwargs.get("importance")

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                # Check if already superseded
                existing = memory_service.get_topical_memory(session, memory_id)
                if not existing:
                    return ToolResult(
                        status="error", tool_response=f"Topic memory with ID {memory_id} not found."
                    )
                if existing.superseded_by_id is not None:
                    return ToolResult(
                        status="error",
                        tool_response=f"Memory ID {memory_id} has already been superseded. Update the current entry (ID {existing.superseded_by_id}) instead.",
                    )

                new_entry = memory_service.supersede_topical_memory(
                    session,
                    memory_id,
                    new_content=content,
                    new_subject=subject,
                    new_tags=tags,
                )

                if not new_entry:
                    return ToolResult(status="error", tool_response="Failed to create new revision.")

                new_entry_id = new_entry.id
                if new_entry_id is None:
                    return ToolResult(status="error", tool_response="Failed to retrieve new revision ID.")

                return ToolResult(
                    status="success",
                    tool_response=f"Memory updated. New revision ID: {new_entry_id}, old revision (ID {memory_id}) superseded. Pinned to clipboard.",
                    entities_to_track=[
                        _make_memory_entity("memory_topic", new_entry_id, "detail", 10),
                    ],
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to update memory: {e}")

        return ToolResult(status="error", tool_response="Memory session unavailable.")


class DeleteMemoryTool(BaseTool):
    """Delete a memory by ID."""

    name = "delete_memory"
    description = (
        "Permanently delete a memory. This cannot be undone. "
        "For topics, the old revisions remain in the database but are marked as superseded "
        "by a null ID — only the most recent entry in a chain can truly be deleted. "
        "NOTE: Events are append-only — prefer not deleting them to preserve history."
    )
    parameters = {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer", "description": "The ID of the memory to delete."},
            "memory_type": {
                "type": "string",
                "enum": ["event", "topic"],
                "description": "The type of memory ('event' or 'topic').",
            },
        },
        "required": ["memory_id", "memory_type"],
    }

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        memory_id: int | None = kwargs.get("memory_id")
        memory_type: str | None = kwargs.get("memory_type")

        if not memory_id or not memory_type:
            return ToolResult(status="error", tool_response="memory_id and memory_type are required.")

        if memory_type not in ("event", "topic"):
            return ToolResult(status="error", tool_response="memory_type must be 'event' or 'topic'.")

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                if memory_type == "event":
                    deleted = memory_service.delete_event_log(session, memory_id)
                else:
                    deleted = memory_service.delete_topical_memory(session, memory_id)

                if not deleted:
                    return ToolResult(
                        status="error", tool_response=f"Memory {memory_type} with ID {memory_id} not found."
                    )

                return ToolResult(
                    status="success",
                    tool_response=f"Memory {memory_type} ID {memory_id} deleted successfully.",
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to delete memory: {e}")

        return ToolResult(status="error", tool_response="Memory session unavailable.")


class RebuildFtsIndexTool(BaseTool):
    """Rebuild the FTS5 full-text search index from all existing memories.

    Use this if search results seem incomplete or the FTS index has gone out of sync.
    This re-indexes all EventLog and TopicalMemory records into the FTS5 virtual table.
    """

    name = "rebuild_fts_index"
    description = (
        "Rebuild the full-text search index. Use this if searches are not finding existing memories."
    )
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, memory_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not memory_db_url:
            return ToolResult(status="error", tool_response="Memory database connection not available.")

        try:
            for session in get_memory_session(memory_db_url=memory_db_url):
                counts = memory_service.rebuild_fts_index(session)
                return ToolResult(
                    status="success",
                    tool_response=f"FTS index rebuilt: {counts['events']} events, {counts['topics']} topics indexed.",
                )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to rebuild FTS index: {e}")

        return ToolResult(status="error", tool_response="Memory session unavailable.")
