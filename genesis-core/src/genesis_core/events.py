"""
Event system for genesis_core.

Single EventBus per GenesisCore. Multi-producer, multi-subscriber with
per-subscriber queues and source-based filtering.

Producers publish CoreEvents with a source string (e.g. "chat:42").
Consumers subscribe with optional source/event_type filters and receive
an async iterator that auto-terminates on STREAM_END for their source.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CoreEventType(Enum):
    STREAM_END = "stream_end"

    # Agent events
    AGENT_REASONING = "agent_reasoning"
    AGENT_CONTENT = "agent_content"
    AGENT_TOOL_START = "agent_tool_start"
    AGENT_TOOL_RESULT = "agent_tool_result"
    AGENT_TOKEN_USAGE = "agent_token_usage"
    AGENT_CLIPBOARD_SNAPSHOT = "agent_clipboard_snapshot"

    # Workflow events
    WORKFLOW_STEP_START = "workflow_step_start"
    WORKFLOW_STEP_COMPLETED = "workflow_step_complete"
    WORKFLOW_STEP_FAILED = "workflow_step_failed"
    WORKFLOW_LOG = "workflow_log"


@dataclass
class CoreEvent:
    """A single event emitted by an agent or workflow run."""

    event_type: CoreEventType
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    index: int | None = None


def chat_source(session_id: int) -> str:
    return f"chat:{session_id}"


def workflow_source(job_id: int) -> str:
    return f"workflow:{job_id}"


class _Subscription:
    def __init__(
        self,
        source: str | None = None,
        event_types: set[CoreEventType] | None = None,
    ):
        self.queue: asyncio.Queue[CoreEvent | None] = asyncio.Queue(maxsize=1024)
        self.source = source
        self.event_types = event_types

    def matches(self, event: CoreEvent) -> bool:
        if event.event_type == CoreEventType.STREAM_END:
            return True  # STREAM_END always passes through to all subscribers
        if self.source is not None and event.source != self.source:
            return False
        if self.event_types is not None and event.event_type not in self.event_types:
            return False
        return True

    def is_end(self, event: CoreEvent) -> bool:
        return (
            event.event_type == CoreEventType.STREAM_END
            and self.source is not None
            and event.source == self.source
        )


class EventBus:
    """In-process async pub/sub for agent/workflow streaming events.

    Single instance per GenesisCore. Supports multiple producers and
    multiple subscribers with per-subscriber queues and filtering.
    """

    def __init__(self):
        self._subscriptions: list[_Subscription] = []

    # --- Raw API ---

    async def publish(self, event: CoreEvent) -> None:
        """Publish an event to all matching subscribers."""
        for sub in list(self._subscriptions):
            if sub.matches(event):
                try:
                    sub.queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def subscribe(
        self,
        source: str | None = None,
        event_types: set[CoreEventType] | None = None,
    ) -> AsyncIterator[CoreEvent]:
        """Subscribe to events. Returns an async iterator.

        Args:
            source: If set, only receive events from this source.
            event_types: If set, only receive these event types.
        """
        sub = _Subscription(source=source, event_types=event_types)
        self._subscriptions.append(sub)
        return self._iterate(sub)

    # --- Chat convenience ---

    async def emit_chat(
        self,
        session_id: int,
        event_type: CoreEventType,
        data: dict[str, Any],
        index: int | None = None,
    ) -> None:
        """Publish a chat event for the given session."""
        await self.publish(CoreEvent(
            event_type=event_type,
            source=chat_source(session_id),
            data=data,
            index=index,
        ))

    async def end_chat_stream(self, session_id: int) -> None:
        """Signal that the chat stream for this session has ended."""
        await self.publish(CoreEvent(
            event_type=CoreEventType.STREAM_END,
            source=chat_source(session_id),
        ))

    def on_chat(self, session_id: int) -> AsyncIterator[CoreEvent]:
        """Subscribe to all events for a chat session. Auto-terminates on STREAM_END."""
        return self.subscribe(source=chat_source(session_id))

    # --- Workflow convenience ---

    async def emit_workflow(
        self,
        job_id: int,
        event_type: CoreEventType,
        data: dict[str, Any],
        index: int | None = None,
    ) -> None:
        """Publish a workflow event for the given job."""
        await self.publish(CoreEvent(
            event_type=event_type,
            source=workflow_source(job_id),
            data=data,
            index=index,
        ))

    async def end_workflow_stream(self, job_id: int) -> None:
        """Signal that the workflow stream for this job has ended."""
        await self.publish(CoreEvent(
            event_type=CoreEventType.STREAM_END,
            source=workflow_source(job_id),
        ))

    def on_workflow(self, job_id: int) -> AsyncIterator[CoreEvent]:
        """Subscribe to all events for a workflow job. Auto-terminates on STREAM_END."""
        return self.subscribe(source=workflow_source(job_id))

    # --- Lifecycle ---

    async def shutdown(self) -> None:
        """Signal all subscribers that the bus is shutting down."""
        for sub in list(self._subscriptions):
            try:
                sub.queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    # --- Internals ---

    async def _iterate(self, sub: _Subscription) -> AsyncIterator[CoreEvent]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
                    if event is None:
                        return
                    if sub.is_end(event):
                        yield event
                        return
                    yield event
                except TimeoutError:
                    continue
        finally:
            self._unsubscribe(sub)

    def _unsubscribe(self, sub: _Subscription) -> None:
        try:
            self._subscriptions.remove(sub)
        except ValueError:
            pass