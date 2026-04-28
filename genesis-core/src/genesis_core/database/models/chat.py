from datetime import UTC, datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class ChatSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_id: str  # e.g., "researcher_agent"
    title: str

    # Concurrency Lock
    is_running: bool = Field(default=False)

    # Store the exact dump of AgentClipboard
    clipboard_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id", index=True)

    # The raw dictionary from genesis_core (role, content, tool_calls, etc.)
    payload: dict[str, Any] = Field(sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
