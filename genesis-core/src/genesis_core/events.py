"""
Event system for genesis_core.

Provides an in-process async pub/sub for agent and workflow streaming events.
Consumers (like genesis_server) subscribe to events and adapt them to their
transport (e.g., SSE).
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CoreEventType(Enum):
    # Agent events (during step)
    AGENT_REASONING = "reasoning"
    AGENT_CONTENT = "content"
    AGENT_TOOL_START = "tool_start"
    AGENT_TOOL_RESULT = "tool_result"
    AGENT_TOKEN_USAGE = "token_usage"
    AGENT_CLIPBOARD_SNAPSHOT = "clipboard"

    # Workflow events
    WORKFLOW_STEP_START = "workflow_step_start"
    WORKFLOW_STEP_COMPLETED = "workflow_step_complete"
    WORKFLOW_STEP_FAILED = "workflow_step_failed"
    WORKFLOW_LOG = "workflow_log"


@dataclass
class CoreEvent:
    """A single event emitted by an agent or workflow run."""

    event_type: CoreEventType
    session_id: int | None = None
    workflow_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    index: int | None = None


class EventBus:
    """In-process async pub/sub for agent/workflow streaming events."""

    def __init__(self):
        self._queue: asyncio.Queue[CoreEvent] = asyncio.Queue()
        self._done = False

    async def publish(self, event: CoreEvent) -> None:
        """Publish a single event to the bus."""
        await self._queue.put(event)

    def subscribe(self) -> AsyncIterator[CoreEvent]:
        """Iterate over events published to this bus."""
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[CoreEvent]:
        """Internal iterator."""
        while not self._done:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield event
            except TimeoutError:
                continue

    def done(self) -> None:
        """Signal that no more events will be published."""
        self._done = True
        # Drain the queue to unblock any waiting subscribers
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
