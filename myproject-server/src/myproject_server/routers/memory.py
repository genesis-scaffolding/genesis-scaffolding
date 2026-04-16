from typing import Literal

from fastapi import APIRouter, Body, HTTPException, status
from myproject_core.persistent_memory.models import EventLog, TopicalMemory
from myproject_core.persistent_memory.service import (
    create_event_log,
    create_topical_memory,
    delete_event_log,
    delete_topical_memory,
    get_event_log,
    get_memory_tag_counts,
    get_revision_chain,
    get_topical_memory,
    list_event_logs,
    list_topical_memories,
    search_memories,
    supersede_topical_memory,
    update_topical_memory,
)

from ..dependencies import MemorySessionDep
from ..schemas.memory import (
    EventLogCreate,
    EventLogRead,
    EventLogUpdate,
    MemoryListResponse,
    MemorySource,
    TagCountResponse,
    TopicalMemoryCreate,
    TopicalMemoryRead,
    TopicalMemoryRevisionChain,
    TopicalMemoryUpdate,
)

router = APIRouter(prefix="/memory", tags=["memory"])


def _event_to_read(e: EventLog) -> EventLogRead:
    return EventLogRead(
        id=e.id,  # type: ignore[reportArgumentType]
        subject=e.subject,
        event_time=e.event_time,
        content=e.content,
        tags=e.tags or [],
        importance=e.importance,
        source=MemorySource(e.source.value if hasattr(e.source, "value") else e.source),  # type: ignore[reportArgumentType]
        related_memory_ids=e.related_memory_ids or [],
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def _topic_to_read(t: TopicalMemory) -> TopicalMemoryRead:
    return TopicalMemoryRead(
        id=t.id,  # type: ignore[reportArgumentType]
        subject=t.subject,
        content=t.content,
        tags=t.tags or [],
        importance=t.importance,
        source=MemorySource(t.source.value if hasattr(t.source, "value") else t.source),  # type: ignore[reportArgumentType]
        superseded_by_id=t.superseded_by_id,
        supersedes_ids=t.supersedes_ids or [],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# --- Events ---


@router.get("/events", response_model=list[EventLogRead])
async def list_events(
    session: MemorySessionDep,
    tag: str | None = None,
    importance: int | None = None,
    source: MemorySource | None = None,
    sort_by: Literal["event_time", "created_at", "importance"] = "event_time",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List all event logs with optional filtering."""
    source_filter = MemorySource(source) if source else None
    events = list_event_logs(
        session,
        tag=tag,
        importance=importance,
        source=source_filter,  # type: ignore[reportArgumentType]
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return [_event_to_read(e) for e in events]


@router.get("/events/{event_id}", response_model=EventLogRead)
async def get_event(event_id: int, session: MemorySessionDep):
    """Get a specific event log by ID."""
    event = get_event_log(session, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_to_read(event)


@router.post("/events", response_model=EventLogRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventLogCreate, session: MemorySessionDep):
    """Create a new event log entry."""
    data = payload.model_dump()
    data["source"] = MemorySource.USER_MANUAL
    event = create_event_log(session, data)
    return _event_to_read(event)


@router.patch("/events/{event_id}", response_model=EventLogRead)
async def update_event(event_id: int, payload: EventLogUpdate, session: MemorySessionDep):
    """Update an event log entry."""
    data = payload.model_dump(exclude_unset=True)
    event = get_event_log(session, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in data.items():
        if value is not None and hasattr(event, key):
            setattr(event, key, value)
    session.add(event)
    session.commit()
    session.refresh(event)
    return _event_to_read(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, session: MemorySessionDep):
    """Delete an event log entry."""
    deleted = delete_event_log(session, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return None


# --- Topics ---


@router.get("/topics", response_model=list[TopicalMemoryRead])
async def list_topics(
    session: MemorySessionDep,
    superseded: bool = False,
    tag: str | None = None,
    importance: int | None = None,
    source: MemorySource | None = None,
    sort_by: Literal["created_at", "updated_at", "importance"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List topical memories with optional filtering."""
    source_filter = MemorySource(source) if source else None
    topics = list_topical_memories(
        session,
        superseded=superseded,
        tag=tag,
        importance=importance,
        source=source_filter,  # type: ignore[reportArgumentType]
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return [_topic_to_read(t) for t in topics]


@router.get("/topics/{topic_id}", response_model=TopicalMemoryRead)
async def get_topic(topic_id: int, session: MemorySessionDep):
    """Get a specific topical memory by ID."""
    topic = get_topical_memory(session, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _topic_to_read(topic)


@router.get("/topics/{topic_id}/chain", response_model=TopicalMemoryRevisionChain)
async def get_topic_chain(topic_id: int, session: MemorySessionDep):
    """Get a topical memory with its full revision chain."""
    current = get_topical_memory(session, topic_id)
    if not current:
        raise HTTPException(status_code=404, detail="Topic not found")
    chain = get_revision_chain(session, topic_id)
    return TopicalMemoryRevisionChain(
        current=_topic_to_read(current),
        chain=[_topic_to_read(t) for t in chain if t.id != current.id],
    )


@router.post("/topics", response_model=TopicalMemoryRead, status_code=status.HTTP_201_CREATED)
async def create_topic(payload: TopicalMemoryCreate, session: MemorySessionDep):
    """Create a new topical memory entry."""
    data = payload.model_dump()
    data["source"] = MemorySource.USER_MANUAL
    topic = create_topical_memory(session, data)
    return _topic_to_read(topic)


@router.patch("/topics/{topic_id}", response_model=TopicalMemoryRead)
async def update_topic(topic_id: int, payload: TopicalMemoryUpdate, session: MemorySessionDep):
    """Update a topical memory entry in-place (for minor changes)."""
    data = payload.model_dump(exclude_unset=True)
    topic = update_topical_memory(session, topic_id, data)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _topic_to_read(topic)


@router.post("/topics/{topic_id}/supersede", response_model=TopicalMemoryRead)
async def supersede_topic(
    topic_id: int,
    session: MemorySessionDep,
    content: str = Body(..., embed=True),
    subject: str | None = None,
    tags: list[str] | None = None,
):
    """Create a new revision, marking the old one as superseded."""
    topic = supersede_topical_memory(session, topic_id, content, subject, tags)
    if not topic:
        raise HTTPException(
            status_code=400, detail="Could not supersede topic. It may already be superseded."
        )
    return _topic_to_read(topic)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(topic_id: int, session: MemorySessionDep):
    """Delete a topical memory entry."""
    deleted = delete_topical_memory(session, topic_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Topic not found")
    return None


# --- Unified endpoints ---


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    session: MemorySessionDep,
    memory_type: Literal["event", "topic", "all"] = "all",
    tag: str | None = None,
    importance: int | None = None,
    source: MemorySource | None = None,
    superseded: bool = False,
    sort_by: Literal["event_time", "created_at", "updated_at", "importance"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List all memories (events and topics) with optional filtering."""
    source_filter = MemorySource(source) if source else None

    events = []
    topics = []

    if memory_type in ("event", "all"):
        events = list_event_logs(
            session,
            tag=tag,
            importance=importance,
            source=source_filter,  # type: ignore[reportArgumentType]
            sort_by=sort_by if sort_by in ("event_time", "created_at", "importance") else "created_at",
            order=order,
            limit=limit,
            offset=offset,
        )

    if memory_type in ("topic", "all"):
        topics = list_topical_memories(
            session,
            superseded=superseded,
            tag=tag,
            importance=importance,
            source=source_filter,  # type: ignore[reportArgumentType]
            sort_by=sort_by if sort_by in ("created_at", "updated_at", "importance") else "updated_at",
            order=order,
            limit=limit,
            offset=offset,
        )

    return MemoryListResponse(
        events=[_event_to_read(e) for e in events],
        topics=[_topic_to_read(t) for t in topics],
    )


@router.get("/tags", response_model=TagCountResponse)
async def get_tags(session: MemorySessionDep):
    """Get tag counts across all current memories."""
    counts = get_memory_tag_counts(session)
    return TagCountResponse(tag_counts=counts)


@router.get("/search", response_model=MemoryListResponse)
async def search_memory(
    session: MemorySessionDep,
    q: str,
    memory_type: Literal["event", "topic", "all"] = "all",
    limit: int = 20,
):
    """Full-text search across memories using FTS5."""
    results = search_memories(session, q, memory_type, limit)
    return MemoryListResponse(
        events=[_event_to_read(e) for e in results["events"]],  # type: ignore[reportArgumentType]
        topics=[_topic_to_read(t) for t in results["topics"]],  # type: ignore[reportArgumentType]
    )
