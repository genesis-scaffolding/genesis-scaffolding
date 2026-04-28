from typing import Literal

from fastapi import APIRouter, Body, HTTPException, status

from genesis_server.dependencies import CoreDep
from genesis_server.schemas.memory import (
    EventLogCreate,
    EventLogRead,
    EventLogUpdate,
    MemoryListResponse,
    TagCountResponse,
    TopicalMemoryCreate,
    TopicalMemoryRead,
    TopicalMemoryRevisionChain,
    TopicalMemoryUpdate,
)
from genesis_server.schemas.memory import (
    MemorySource as ServerMemorySource,
)

router = APIRouter(prefix="/memory", tags=["memory"])


def _event_to_read(e) -> EventLogRead:
    # Build a dict from the genesis_core model, converting the enum to our schema's enum
    source_val = e.source.value if hasattr(e.source, "value") else e.source
    data = {
        "id": e.id,
        "subject": e.subject,
        "event_time": e.event_time,
        "content": e.content,
        "tags": e.tags or [],
        "importance": e.importance,
        "source": ServerMemorySource(source_val),
        "related_memory_ids": e.related_memory_ids or [],
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }
    return EventLogRead.model_validate(data)


def _topic_to_read(t) -> TopicalMemoryRead:
    source_val = t.source.value if hasattr(t.source, "value") else t.source
    data = {
        "id": t.id,
        "subject": t.subject,
        "content": t.content,
        "tags": t.tags or [],
        "importance": t.importance,
        "source": ServerMemorySource(source_val),
        "superseded_by_id": t.superseded_by_id,
        "supersedes_ids": t.supersedes_ids or [],
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
    return TopicalMemoryRead.model_validate(data)


# --- Events ---


@router.get("/events", response_model=list[EventLogRead])
async def list_events(
    core: CoreDep,
    tag: str | None = None,
    importance: int | None = None,
    source: ServerMemorySource | None = None,
    sort_by: Literal["event_time", "created_at", "importance"] = "event_time",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List all event logs with optional filtering."""
    from genesis_core.persistent_memory.models import MemorySource as GcMemorySource
    gc_source = GcMemorySource(str(source.value)) if source else None
    events = core.memory_manager.list_event_logs(
        tag=tag,
        importance=importance,
        source=gc_source,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return [_event_to_read(e) for e in events]


@router.get("/events/{event_id}", response_model=EventLogRead)
async def get_event(event_id: int, core: CoreDep):
    """Get a specific event log by ID."""
    event = core.memory_manager.get_event_log(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_to_read(event)


@router.post("/events", response_model=EventLogRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventLogCreate, core: CoreDep):
    """Create a new event log entry."""
    data = payload.model_dump()
    data["source"] = ServerMemorySource.USER_MANUAL
    event = core.memory_manager.create_event_log(data)
    return _event_to_read(event)


@router.patch("/events/{event_id}", response_model=EventLogRead)
async def update_event(event_id: int, payload: EventLogUpdate, core: CoreDep):
    """Update an event log entry."""
    data = payload.model_dump(exclude_unset=True)
    event = core.memory_manager.get_event_log(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in data.items():
        if value is not None and hasattr(event, key):
            setattr(event, key, value)
    core.memory_manager.update_event_log(event_id, data)
    return _event_to_read(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, core: CoreDep):
    """Delete an event log entry."""
    if not core.memory_manager.delete_event_log(event_id):
        raise HTTPException(status_code=404, detail="Event not found")


# --- Topics ---


@router.get("/topics", response_model=list[TopicalMemoryRead])
async def list_topics(
    core: CoreDep,
    superseded: bool = False,
    tag: str | None = None,
    importance: int | None = None,
    source: ServerMemorySource | None = None,
    sort_by: Literal["created_at", "updated_at", "importance"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List topical memories with optional filtering."""
    from genesis_core.persistent_memory.models import MemorySource as GcMemorySource
    gc_source = GcMemorySource(str(source.value)) if source else None
    topics = core.memory_manager.list_topical_memories(
        superseded=superseded,
        tag=tag,
        importance=importance,
        source=gc_source,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return [_topic_to_read(t) for t in topics]


@router.get("/topics/{topic_id}", response_model=TopicalMemoryRead)
async def get_topic(topic_id: int, core: CoreDep):
    """Get a specific topical memory by ID."""
    topic = core.memory_manager.get_topical_memory(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _topic_to_read(topic)


@router.get("/topics/{topic_id}/chain", response_model=TopicalMemoryRevisionChain)
async def get_topic_chain(topic_id: int, core: CoreDep):
    """Get a topical memory with its full revision chain."""
    current = core.memory_manager.get_topical_memory(topic_id)
    if not current:
        raise HTTPException(status_code=404, detail="Topic not found")
    chain = core.memory_manager.get_revision_chain(topic_id)
    return TopicalMemoryRevisionChain(
        current=_topic_to_read(current),
        chain=[_topic_to_read(t) for t in chain if t.id != current.id],
    )


@router.post("/topics", response_model=TopicalMemoryRead, status_code=status.HTTP_201_CREATED)
async def create_topic(payload: TopicalMemoryCreate, core: CoreDep):
    """Create a new topical memory entry."""
    data = payload.model_dump()
    data["source"] = ServerMemorySource.USER_MANUAL
    topic = core.memory_manager.create_topical_memory(data)
    return _topic_to_read(topic)


@router.patch("/topics/{topic_id}", response_model=TopicalMemoryRead)
async def update_topic(topic_id: int, payload: TopicalMemoryUpdate, core: CoreDep):
    """Update a topical memory entry in-place."""
    topic = core.memory_manager.update_topical_memory(topic_id, payload.model_dump(exclude_unset=True))
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _topic_to_read(topic)


@router.post("/topics/{topic_id}/supersede", response_model=TopicalMemoryRead)
async def supersede_topic(
    topic_id: int,
    core: CoreDep,
    content: str = Body(..., embed=True),
    subject: str | None = None,
    tags: list[str] | None = None,
):
    """Create a new revision, marking the old one as superseded."""
    topic = core.memory_manager.supersede_topical_memory(topic_id, content, subject, tags)
    if not topic:
        raise HTTPException(
            status_code=400, detail="Could not supersede topic. It may already be superseded.",
        )
    return _topic_to_read(topic)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(topic_id: int, core: CoreDep):
    """Delete a topical memory entry."""
    if not core.memory_manager.delete_topical_memory(topic_id):
        raise HTTPException(status_code=404, detail="Topic not found")


# --- Unified endpoints ---


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    core: CoreDep,
    memory_type: Literal["event", "topic", "all"] = "all",
    tag: str | None = None,
    importance: int | None = None,
    source: ServerMemorySource | None = None,
    superseded: bool = False,
    sort_by: Literal["event_time", "created_at", "updated_at", "importance"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """List all memories (events and topics) with optional filtering."""
    from genesis_core.persistent_memory.models import MemorySource as GcMemorySource
    gc_source = GcMemorySource(str(source.value)) if source else None
    events = []
    topics = []

    if memory_type in ("event", "all"):
        events_sort = sort_by if sort_by in ("event_time", "created_at", "importance") else "created_at"
        events = core.memory_manager.list_event_logs(
            tag=tag,
            importance=importance,
            source=gc_source,
            sort_by=events_sort,
            order=order,
            limit=limit,
            offset=offset,
        )

    if memory_type in ("topic", "all"):
        topics_sort = sort_by if sort_by in ("created_at", "updated_at", "importance") else "updated_at"
        topics = core.memory_manager.list_topical_memories(
            superseded=superseded,
            tag=tag,
            importance=importance,
            source=gc_source,
            sort_by=topics_sort,
            order=order,
            limit=limit,
            offset=offset,
        )

    return MemoryListResponse(
        events=[_event_to_read(e) for e in events],
        topics=[_topic_to_read(t) for t in topics],
    )


@router.get("/tags", response_model=TagCountResponse)
async def get_tags(core: CoreDep):
    """Get tag counts across all current memories."""
    counts = core.memory_manager.get_memory_tag_counts()
    return TagCountResponse(tag_counts=counts)


@router.get("/search", response_model=MemoryListResponse)
async def search_memory(
    core: CoreDep,
    q: str,
    memory_type: Literal["event", "topic", "all"] = "all",
    limit: int = 20,
):
    """Full-text search across memories using FTS5."""
    results = core.memory_manager.search_memories(q, memory_type, limit)
    return MemoryListResponse(
        events=[_event_to_read(e) for e in results.get("events", [])],
        topics=[_topic_to_read(t) for t in results.get("topics", [])],
    )
