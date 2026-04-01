from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.sql import cast
from sqlalchemy.types import String
from sqlmodel import Session, col

from .models import EventLog, MemorySource, TopicalMemory

# --- EVENT LOG ---


def create_event_log(session: Session, data: dict[str, Any]) -> EventLog:
    """Create a new event log entry."""
    db_entry = EventLog.model_validate(data)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


def get_event_log(session: Session, event_id: int) -> EventLog | None:
    """Get a specific event log by ID."""
    return session.get(EventLog, event_id)


def list_event_logs(
    session: Session,
    tag: str | None = None,
    importance: int | None = None,
    source: MemorySource | None = None,
    sort_by: Literal["event_time", "created_at", "importance"] = "event_time",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
) -> list[EventLog]:
    """List event logs with optional filtering."""
    q = session.query(EventLog)

    if tag:
        tag_pattern = f'%"{tag}"%'
        q = q.filter(cast(EventLog.tags, String).like(tag_pattern))  # type: ignore[arg-type]
    if importance is not None:
        q = q.filter(EventLog.importance == importance)  # type: ignore[arg-type]
    if source is not None:
        q = q.filter(EventLog.source == source)  # type: ignore

    order_field = getattr(EventLog, sort_by)
    if order == "desc":
        q = q.order_by(col(order_field).desc())
    else:
        q = q.order_by(col(order_field).asc())
    return q.limit(limit).offset(offset).all()  # type: ignore[return-value]


def delete_event_log(session: Session, event_id: int) -> bool:
    """Delete an event log. Returns True if deleted, False if not found."""
    entry = session.get(EventLog, event_id)
    if not entry:
        return False
    session.delete(entry)
    session.commit()
    return True


# --- TOPICAL MEMORY ---


def create_topical_memory(session: Session, data: dict[str, Any]) -> TopicalMemory:
    """Create a new topical memory entry."""
    db_entry = TopicalMemory.model_validate(data)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


def get_topical_memory(session: Session, memory_id: int) -> TopicalMemory | None:
    """Get a specific topical memory by ID."""
    return session.get(TopicalMemory, memory_id)


def list_topical_memories(
    session: Session,
    superseded: bool = False,
    tag: str | None = None,
    importance: int | None = None,
    source: MemorySource | None = None,
    sort_by: Literal["created_at", "updated_at", "importance"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
) -> list[TopicalMemory]:
    """List topical memories. By default excludes superseded (old) entries."""
    q = session.query(TopicalMemory)

    if superseded:
        q = q.filter(TopicalMemory.superseded_by_id.isnot(None))  # type: ignore
    else:
        q = q.filter(TopicalMemory.superseded_by_id.is_(None))  # type: ignore

    if tag:
        tag_pattern = f'%"{tag}"%'
        q = q.filter(cast(TopicalMemory.tags, String).like(tag_pattern))  # type: ignore[arg-type]
    if importance is not None:
        q = q.filter(TopicalMemory.importance == importance)  # type: ignore[arg-type]
    if source is not None:
        q = q.filter(TopicalMemory.source == source)  # type: ignore

    order_field = getattr(TopicalMemory, sort_by)
    if order == "desc":
        q = q.order_by(col(order_field).desc())
    else:
        q = q.order_by(col(order_field).asc())
    return q.limit(limit).offset(offset).all()  # type: ignore[return-value]


def update_topical_memory(
    session: Session,
    memory_id: int,
    data: dict[str, Any],
) -> TopicalMemory | None:
    """Update a topical memory's fields in-place. Use supersede_topical_memory for revision history."""
    db_entry = session.get(TopicalMemory, memory_id)
    if not db_entry:
        return None
    for key, value in data.items():
        if hasattr(db_entry, key):
            setattr(db_entry, key, value)
    db_entry.updated_at = datetime.now(UTC)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


def supersede_topical_memory(
    session: Session,
    memory_id: int,
    new_content: str,
    new_subject: str | None = None,
    new_tags: list[str] | None = None,
) -> TopicalMemory | None:
    """Create a new revision, marking the old one as superseded.

    This preserves the full revision chain instead of overwriting in-place.
    """
    old_entry = session.get(TopicalMemory, memory_id)
    if not old_entry:
        return None
    if old_entry.superseded_by_id is not None:
        # Already superseded — creating a new revision from an already-superseded entry
        # We could either reject this or walk back to find the actual current entry.
        # For safety, we reject.
        return None

    new_entry = TopicalMemory(
        subject=new_subject if new_subject is not None else old_entry.subject,
        content=new_content,
        tags=new_tags if new_tags is not None else old_entry.tags,
        importance=old_entry.importance,
        source=MemorySource.AGENT_TOOL,
        superseded_by_id=None,
        supersedes_ids=[memory_id],
    )
    session.add(new_entry)
    session.flush()  # Get new_entry.id

    # Mark old entry as superseded
    old_entry.superseded_by_id = new_entry.id
    session.add(old_entry)
    session.commit()
    session.refresh(new_entry)
    return new_entry


def get_revision_chain(
    session: Session,
    memory_id: int,
) -> list[TopicalMemory]:
    """Walk the revision chain backwards from a memory ID.

    Returns list from oldest to newest (the chain from original to current).
    """
    chain = []
    current_id = memory_id

    while current_id is not None:
        entry = session.get(TopicalMemory, current_id)
        if not entry:
            break
        chain.append(entry)
        current_id = entry.superseded_by_id

    return chain


def delete_topical_memory(session: Session, memory_id: int) -> bool:
    """Delete a topical memory. Returns True if deleted, False if not found."""
    entry = session.get(TopicalMemory, memory_id)
    if not entry:
        return False
    session.delete(entry)
    session.commit()
    return True


# --- UNIFIED SEARCH ---


def search_memories(
    session: Session,
    query: str,
    memory_type: Literal["event", "topic", "all"] = "all",
    limit: int = 20,
) -> dict[str, list[EventLog | TopicalMemory]]:
    """Full-text search using FTS5 with porter stemming.

    Returns dict with 'events' and 'topics' keys.
    Only returns current (non-superseded) topical memories.
    """
    if not query.strip():
        return {"events": [], "topics": []}

    # FTS5 query: all terms must match (AND), porter tokenizer handles stemming
    # superseded_by_id IS NULL filter ensures we only get current topics
    if memory_type == "event":
        type_filter = "table_type = 'event'"
        superseded_filter = "1=1"
    elif memory_type == "topic":
        type_filter = "table_type = 'topic'"
        superseded_filter = "superseded_by_id IS NULL"
    else:
        type_filter = "1=1"
        superseded_filter = "1=1"

    fts_sql = text(f"""
        SELECT id, table_type, bm25(memory_fts) as score
        FROM memory_fts
        WHERE memory_fts MATCH :query AND {type_filter} AND {superseded_filter}
        ORDER BY score
        LIMIT :limit
    """)
    fts_results: list[Any] = list(session.execute(fts_sql, {"query": query, "limit": limit}).all())  # type: ignore[arg-type,return-value]

    if not fts_results:
        return {"events": [], "topics": []}

    event_ids = [r.id for r in fts_results if r.table_type == "event"]
    topic_ids = [r.id for r in fts_results if r.table_type == "topic"]

    events: list[EventLog] = []
    topics: list[TopicalMemory] = []

    if event_ids:
        events = list(session.query(EventLog).filter(EventLog.id.in_(event_ids)).all())  # type: ignore[arg-type]
    if topic_ids:
        topics = list(session.query(TopicalMemory).filter(TopicalMemory.id.in_(topic_ids)).all())  # type: ignore[arg-type]

    return {"events": events, "topics": topics}  # type: ignore[return-value]


def rebuild_fts_index(session: Session) -> dict[str, int]:
    """Rebuild the FTS5 index from all existing EventLog and TopicalMemory records.

    Use this to repopulate the FTS index if it has gone out of sync,
    or to initially index existing data after adding FTS5 to an existing database.
    Returns counts of indexed events and topics.
    """
    # Clear existing FTS entries
    session.execute(text("DELETE FROM memory_fts"))
    session.commit()

    # Re-index all EventLog records
    events = session.query(EventLog).all()  # type: ignore[return-value]
    event_count = 0
    for e in events:
        session.execute(
            text(
                "INSERT INTO memory_fts(id, table_type, subject, content, superseded_by_id) "
                "VALUES (:id, 'event', :subject, :content, NULL)"
            ),
            {"id": e.id, "subject": e.subject, "content": e.content},
        )
        event_count += 1

    # Re-index all TopicalMemory records
    topics = session.query(TopicalMemory).all()  # type: ignore[return-value]
    topic_count = 0
    for t in topics:
        session.execute(
            text(
                "INSERT INTO memory_fts(id, table_type, subject, content, superseded_by_id) "
                "VALUES (:id, 'topic', :subject, :content, :superseded_by_id)"
            ),
            {"id": t.id, "subject": t.subject, "content": t.content, "superseded_by_id": t.superseded_by_id},
        )
        topic_count += 1

    session.commit()
    return {"events": event_count, "topics": topic_count}


# --- TAG COUNTS ---


def get_memory_tag_counts(session: Session) -> dict[str, int]:
    """Returns {tag: count} for all tags across current (non-superseded) memories.

    Count is deduplicated per memory — if a single memory has the same tag twice,
    it counts once. Events and topics are pooled together.
    Only considers:
    - EventLog rows (all events are current by nature — append-only)
    - TopicalMemory rows where superseded_by_id IS NULL (current revisions only)
    """
    tag_counts: dict[str, int] = {}

    # Count tags from EventLog (all events are current — append-only)
    event_tag_sql = text("""
        SELECT value as tag
        FROM eventlog, json_each(eventlog.tags)
        WHERE eventlog.tags IS NOT NULL AND json_each.value IS NOT NULL
    """)
    for row in session.execute(event_tag_sql).all():
        tag = row.tag
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Count tags from current TopicalMemory (non-superseded)
    topic_tag_sql = text("""
        SELECT value as tag
        FROM topicalmemory, json_each(topicalmemory.tags)
        WHERE topicalmemory.tags IS NOT NULL
          AND json_each.value IS NOT NULL
          AND topicalmemory.superseded_by_id IS NULL
    """)
    for row in session.execute(topic_tag_sql).all():
        tag = row.tag
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return tag_counts


def get_topical_memory_by_subject(session: Session, subject: str) -> TopicalMemory | None:
    """Lookup a TopicalMemory by its subject field. Returns the current (non-superseded) entry."""
    return (
        session.query(TopicalMemory)
        .filter(TopicalMemory.subject == subject)  # type: ignore
        .filter(TopicalMemory.superseded_by_id.is_(None))  # type: ignore
        .first()
    )
