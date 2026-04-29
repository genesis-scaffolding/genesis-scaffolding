"""Tests for the EventBus multi-subscriber fan-out system."""

import asyncio

from genesis_core.events import (
    CoreEvent,
    CoreEventType,
    EventBus,
    chat_source,
    workflow_source,
)


def make_chat_event(session_id: int, event_type: CoreEventType, data: dict | None = None) -> CoreEvent:
    return CoreEvent(
        event_type=event_type,
        source=chat_source(session_id),
        data=data or {},
    )


# --- Tests use asyncio.run() so each test gets a fresh event loop ---


def test_single_subscriber_receives_published_event():
    """Subscriber must exist BEFORE events are published."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_first_event(bus.on_chat(1)))
        await _wait_for_subscriber_start()

        await bus.publish(make_chat_event(1, CoreEventType.AGENT_CONTENT, {"chunk": "hello"}))
        await bus.end_chat_stream(1)
        return await asyncio.wait_for(task, timeout=3.0)

    result = asyncio.run(run())
    assert result.data["chunk"] == "hello"


def test_multiple_subscribers_both_receive_events():
    """Two subscribers to the same source both receive the event."""

    async def run():
        bus = EventBus()
        task1 = asyncio.create_task(_collect(bus.on_chat(1)))
        await _wait_for_subscriber_start()
        task2 = asyncio.create_task(_collect(bus.on_chat(1)))
        await _wait_for_subscriber_start()
        await bus.emit_chat(1, CoreEventType.AGENT_CONTENT, {"chunk": "hi"})
        await bus.end_chat_stream(1)
        results1 = await asyncio.wait_for(task1, timeout=3.0)
        results2 = await asyncio.wait_for(task2, timeout=3.0)

        return results1, results2

    (results1, results2) = asyncio.run(run())

    assert len(results1) == 2
    assert len(results2) == 2
    assert results1[0].data["chunk"] == "hi"
    assert results2[0].data["chunk"] == "hi"


def test_subscriber_filtered_by_source_only_gets_matching_events():
    """Subscriber for chat:1 only receives events for session 1, not session 2."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.on_chat(1)))
        await _wait_for_subscriber_start()
        await bus.emit_chat(1, CoreEventType.AGENT_CONTENT, {"chunk": "for 1"})
        await bus.emit_chat(2, CoreEventType.AGENT_CONTENT, {"chunk": "for 2"})
        await bus.end_chat_stream(1)
        await bus.end_chat_stream(2)
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    assert len(events) == 2
    assert events[0].data["chunk"] == "for 1"


def test_subscriber_filtered_by_event_types():
    """Subscriber with event_types filter only receives matching types."""

    async def run():
        bus = EventBus()
        sub = bus.subscribe(source=chat_source(1), event_types={CoreEventType.AGENT_TOOL_START})
        task = asyncio.create_task(_collect(sub))
        await _wait_for_subscriber_start()
        await bus.emit_chat(1, CoreEventType.AGENT_CONTENT, {"chunk": "content"})
        await bus.emit_chat(1, CoreEventType.AGENT_TOOL_START, {"name": "tool"})
        await bus.end_chat_stream(1)
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    assert len(events) == 2  # tool_start + stream_end
    assert events[0].event_type == CoreEventType.AGENT_TOOL_START
    assert events[1].event_type == CoreEventType.STREAM_END


def test_wildcard_subscriber_receives_all_events():
    """Subscriber with source=None receives all events."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.subscribe()))
        await _wait_for_subscriber_start()
        await bus.emit_chat(1, CoreEventType.AGENT_CONTENT, {"chunk": "a"})
        await bus.emit_workflow(10, CoreEventType.WORKFLOW_STEP_START, {"step_id": "s1"})
        await bus.shutdown()
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    assert len(events) == 2  # content + step_start


def test_wildcard_subscriber_not_terminated_by_stream_end():
    """Wildcard subscriber stays alive after STREAM_END."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.subscribe()))
        await _wait_for_subscriber_start()
        await bus.publish(make_chat_event(1, CoreEventType.AGENT_CONTENT, {"chunk": "a"}))
        await bus.end_chat_stream(1)
        await bus.publish(make_chat_event(2, CoreEventType.AGENT_CONTENT, {"chunk": "b"}))
        await bus.end_chat_stream(2)
        await bus.shutdown()
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    print(events)
    assert len(events) == 4  # 2 content + 2 stream_end


def test_source_subscriber_terminates_on_stream_end():
    """Source-bound subscriber exits after receiving STREAM_END."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.on_chat(1)))
        await _wait_for_subscriber_start()
        await bus.publish(make_chat_event(1, CoreEventType.AGENT_CONTENT, {"chunk": "a"}))
        await bus.end_chat_stream(1)
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    types = [e.event_type for e in events]
    assert CoreEventType.AGENT_CONTENT in types
    assert CoreEventType.STREAM_END in types


def test_shutdown_terminates_all_subscribers():
    """bus.shutdown() sends None to all subscribers, terminating their iterators."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.subscribe()))
        await asyncio.sleep(0.05)
        await bus.shutdown()
        return await asyncio.wait_for(task, timeout=2.0)

    result = asyncio.run(run())
    assert result == []


def test_subscription_cleanup_after_iteration():
    """After iterator exits, subscription is removed from bus."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.on_chat(1)))
        await _wait_for_subscriber_start()
        await bus.publish(make_chat_event(1, CoreEventType.AGENT_CONTENT, {"chunk": "x"}))
        await bus.end_chat_stream(1)
        await asyncio.wait_for(task, timeout=3.0)
        return bus._subscriptions

    subs = asyncio.run(run())
    assert len(subs) == 0


def test_convenience_end_chat_stream():
    """end_chat_stream() emits STREAM_END with correct source."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.on_chat(42)))
        await _wait_for_subscriber_start()
        await bus.emit_chat(42, CoreEventType.AGENT_CONTENT, {"chunk": "hi"})
        await bus.end_chat_stream(42)
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    assert any(e.event_type == CoreEventType.STREAM_END for e in events)


def test_convenience_end_workflow_stream():
    """end_workflow_stream() emits STREAM_END with correct source."""

    async def run():
        bus = EventBus()
        task = asyncio.create_task(_collect(bus.on_workflow(99)))
        await _wait_for_subscriber_start()
        await bus.emit_workflow(99, CoreEventType.WORKFLOW_STEP_COMPLETED, {"step_id": "s1"})
        await bus.end_workflow_stream(99)
        return await asyncio.wait_for(task, timeout=3.0)

    events = asyncio.run(run())
    assert any(e.event_type == CoreEventType.STREAM_END for e in events)


def test_chat_source_and_workflow_source_helpers():
    assert chat_source(42) == "chat:42"
    assert workflow_source(7) == "workflow:7"


# --- Internal helpers ---


async def _collect(iterator):
    events = []
    async for event in iterator:
        events.append(event)
    return events


async def _first_event(iterator):
    return await iterator.__anext__()


async def _wait_for_subscriber_start():
    """Allow event loop to start subscriber coroutines."""
    await asyncio.sleep(0)
