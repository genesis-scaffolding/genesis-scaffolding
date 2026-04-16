"""Memory subsystem for persistent agent memory across sessions."""

from .db import get_memory_engine, get_memory_session
from .models import EventLog, MemorySource, TopicalMemory
from .service import (
    create_event_log,
    create_topical_memory,
    delete_event_log,
    delete_topical_memory,
    get_event_log,
    get_memory_tag_counts,
    get_revision_chain,
    get_topical_memory,
    get_topical_memory_by_subject,
    get_user_profile,
    list_event_logs,
    list_topical_memories,
    search_memories,
    supersede_topical_memory,
    update_topical_memory,
)

__all__ = [
    "EventLog",
    "MemorySource",
    "TopicalMemory",
    "create_event_log",
    "create_topical_memory",
    "delete_event_log",
    "delete_topical_memory",
    "get_event_log",
    "get_memory_engine",
    "get_memory_session",
    "get_memory_tag_counts",
    "get_revision_chain",
    "get_topical_memory",
    "get_topical_memory_by_subject",
    "get_user_profile",
    "list_event_logs",
    "list_topical_memories",
    "search_memories",
    "supersede_topical_memory",
    "update_topical_memory",
]
