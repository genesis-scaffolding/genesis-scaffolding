from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, MetaData
from sqlmodel import JSON, Field, SQLModel

# Dedicated metadata — distinct from productivity_metadata and any system-wide metadata
memory_metadata = MetaData()


def get_utc_now():
    """Helper to handle the deprecated utcnow()"""
    return datetime.now(UTC)


class MemorySource(StrEnum):
    AGENT_TOOL = "agent_tool"
    DREAM_WORKFLOW = "dream_workflow"
    USER_MANUAL = "user_manual"


class EventLog(SQLModel, table=True):
    """Append-only log of discrete facts/moments in time. Never overwritten."""

    metadata = memory_metadata
    id: int | None = Field(default=None, primary_key=True)
    subject: str | None = Field(default=None, index=True)  # Optional display label for human browsing
    event_time: datetime = Field(  # When the event actually happened (may differ from created_at)
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    content: str = Field(nullable=False)  # What happened
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))  # Agent-generated tags
    importance: int = Field(default=3, ge=1, le=5)  # Agent-assigned, user-overridable
    source: MemorySource = Field(default=MemorySource.AGENT_TOOL)
    related_memory_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))


class TopicalMemory(SQLModel, table=True):
    """Revisable knowledge with supersession chain. Old versions marked as superseded, not deleted."""

    metadata = memory_metadata
    id: int | None = Field(default=None, primary_key=True)
    subject: str | None = Field(default=None, index=True)  # Optional display label
    content: str = Field(nullable=False)  # Current state of knowledge
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))  # Agent-generated tags
    importance: int = Field(default=3, ge=1, le=5)  # Agent-assigned, user-overridable
    source: MemorySource = Field(default=MemorySource.AGENT_TOOL)
    superseded_by_id: int | None = Field(default=None, foreign_key="topicalmemory.id")  # Newer revision
    supersedes_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))  # IDs this entry supersedes
    created_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
