from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemorySource(StrEnum):
    AGENT_TOOL = "agent_tool"
    DREAM_WORKFLOW = "dream_workflow"
    USER_MANUAL = "user_manual"


class MemoryType(StrEnum):
    EVENT = "event"
    TOPIC = "topic"


# --- Base schemas ---
class EventLogBase(BaseModel):
    subject: str | None = None
    event_time: datetime
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    source: MemorySource = MemorySource.USER_MANUAL


class TopicalMemoryBase(BaseModel):
    subject: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    source: MemorySource = MemorySource.USER_MANUAL


# --- Read schemas (with metadata) ---
class EventLogRead(EventLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    related_memory_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TopicalMemoryRead(TopicalMemoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    superseded_by_id: int | None = None
    supersedes_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TopicalMemoryRevisionChain(BaseModel):
    """A topical memory with its full revision chain."""
    current: TopicalMemoryRead
    chain: list[TopicalMemoryRead]


# --- Create schemas ---
class EventLogCreate(EventLogBase):
    related_memory_ids: list[int] = Field(default_factory=list)


class TopicalMemoryCreate(TopicalMemoryBase):
    pass


# --- Update schemas ---
class EventLogUpdate(BaseModel):
    subject: str | None = None
    event_time: datetime | None = None
    content: str | None = None
    tags: list[str] | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    related_memory_ids: list[int] | None = None


class TopicalMemoryUpdate(BaseModel):
    subject: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    importance: int | None = Field(default=None, ge=1, le=5)


# --- List/Filter schemas ---
class MemoryListParams(BaseModel):
    memory_type: Literal["event", "topic", "all"] = "all"
    tag: str | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    source: MemorySource | None = None
    superseded: bool = False  # Only for topics
    sort_by: Literal["event_time", "created_at", "updated_at", "importance"] = "updated_at"
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=50, le=200)
    offset: int = 0


class MemoryListResponse(BaseModel):
    events: list[EventLogRead] = Field(default_factory=list)
    topics: list[TopicalMemoryRead] = Field(default_factory=list)


class TagCountResponse(BaseModel):
    tag_counts: dict[str, int]