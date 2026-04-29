# EventBus: In-Process Async Pub/Sub for Streaming

## Overview

`EventBus` is the in-process streaming backbone for `genesis-core`. It connects agent/workflow producers to UI consumers via a multi-subscriber, multi-producer fan-out model built on `asyncio.Queue`. Every `GenesisCore` instance owns exactly one `EventBus`, shared across all agents, workflows, and SSE endpoints within that process.

## Problem It Solves

When a user runs an agent or triggers a workflow, multiple parts of the system need to react to the same stream of events simultaneously:

- The **agent loop** emits content chunks, reasoning traces, tool calls, token usage
- The **workflow engine** emits step start/complete/fail events
- The **FastAPI router** needs to forward those events to the browser over SSE
- The **job manager** may need to update database state on step boundaries

Before the EventBus, each consumer managed its own queue or polling loop. This made it impossible for multiple SSE clients (e.g., a browser tab + a CLI monitor) to share the same stream without duplicating all the logic.

## How It Works

### The Big Picture

An `EventBus` instance keeps a list of **subscriptions**. Each subscription is a wrapper around an `asyncio.Queue` — think of it as a named pipe with a label attached. The label tells the bus which events this subscription is interested in.

When a **subscriber** wants to receive events, it calls `bus.subscribe()` (or one of the typed helpers like `on_chat(42)`). This call:

1. Creates a new `_Subscription` object with its own `asyncio.Queue(maxsize=1024)`
2. Attaches a filter label (e.g., "I want only `chat:42` events" or "I want `workflow:7` events")
3. Adds that subscription to the bus's internal list
4. Returns an **async iterator** that the subscriber pulls from

The subscriber then loops over that iterator. It receives events one by one until either the bus tells it the stream is done (by sending a special `STREAM_END` signal), or the queue is closed entirely (e.g., the server is shutting down).

When a **producer** wants to send an event, it calls `bus.publish(event)` (or a helper like `emit_chat(session_id, event_type, data)`). The bus then visits every subscription in its list and, for each one whose filter matches the event, puts a copy of the event into that subscription's queue. If a subscription's queue is full (consumer is slow or disconnected), the event is dropped for that subscription only — all other subscriptions receive it normally.

This is the core design: **one event published, zero to many deliveries**, with each consumer getting its own independent buffer.

### Sources: How Events Are Routed

Every event carries a `source` string — something like `"chat:42"` or `"workflow:7"`. The source tells the bus which pipeline the event belongs to. When a subscription is created, it can specify a source filter. A subscription with `source="chat:42"` will only receive events whose source is `"chat:42"`. A subscription with no source filter receives everything.

There is one special rule: the `STREAM_END` control signal always passes through to every subscription regardless of its source or event-type filter. This ensures that every subscriber — even one that filtered to only receive `AGENT_CONTENT` events — still gets told when to stop.

### Producers and Subscribers

**Producers** are the agent engine and workflow engine. They generate events as they run. They do not know or care how many subscribers are listening; they just publish and move on.

**Subscribers** are typically the FastAPI SSE routers. Each incoming browser connection is one subscriber. It calls `bus.on_chat(session_id)` to get an iterator, loops over it, formats each event as an SSE line, and yields it to the HTTP response. When `STREAM_END` arrives, the iterator ends, the SSE response completes cleanly, and the subscription is automatically removed from the bus.

This separation means producers and consumers are fully decoupled. A producer does not need to know what is listening; a consumer does not need to know what is producing.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│                    EventBus                         │
│                                                     │
│  _subscriptions: list[_Subscription]                │
│                                                     │
│  publish(event) ──────────────────────────────────► │
│       │                           ┌───────────────┐ │
│       ├──────────────────────────►│ sub.queue     │ │  Subscriber A
│       ├──────────────────────────►│ (on_chat(42)) │ │  gets only chat:42
│       └──────────────────────────►│               │ │  events
│                                   └───────────────┘ │
│                                   ┌───────────────┐ │
│                                   │ sub.queue     │ │  Subscriber B
│                                   │ (on_workflow) │ │  gets only workflow:7
│                                   │               │ │  events
│                                   └───────────────┘ │
└─────────────────────────────────────────────────────┘
```

#### `CoreEvent`

The only message type passed through the bus:

```python
@dataclass
class CoreEvent:
    event_type: CoreEventType   # AGENT_CONTENT, WORKFLOW_STEP_START, STREAM_END, etc.
    source: str                 # e.g. "chat:42", "workflow:7"
    data: dict[str, Any]        # arbitrary payload
    index: int | None = None    # optional ordering hint
```

The `source` field is the routing key. All chat events for session 42 carry `source="chat:42"`. All workflow events for job 7 carry `source="workflow:7"`.

#### `CoreEventType`

Enum of all event types in the system. Two categories:

- **Agent events**: `AGENT_REASONING`, `AGENT_CONTENT`, `AGENT_TOOL_START`, `AGENT_TOOL_RESULT`, `AGENT_TOKEN_USAGE`, `AGENT_CLIPBOARD_SNAPSHOT`
- **Workflow events**: `WORKFLOW_STEP_START`, `WORKFLOW_STEP_COMPLETED`, `WORKFLOW_STEP_FAILED`, `WORKFLOW_LOG`
- **Control signal**: `STREAM_END` — signals that a stream has completed

#### `_Subscription`

One per subscriber. Holds the queue and the filter criteria:

```python
class _Subscription:
    queue: asyncio.Queue[CoreEvent | None]   # maxsize=1024
    source: str | None                        # None = all sources
    event_types: set[CoreEventType] | None   # None = all types
```

The `matches()` method determines whether an event should be delivered to this subscriber. `STREAM_END` always passes through to all subscribers regardless of filters — this ensures every subscriber receives the termination signal even if they filtered it to a subset of event types.

#### `EventBus`

The public interface. Maintains a list of `_Subscription` instances.

### How the Fan-Out Works

When `publish(event)` is called:

1. Iterate over `list(self._subscriptions)` (snapshot copy to allow safe removal during iteration)
2. For each subscription, call `sub.matches(event)`
3. If matched, attempt `sub.queue.put_nowait(event)`
4. If the queue is full (`QueueFull`), drop the event silently

This is a **fire-and-forget** broadcast. Producers do not wait for consumers. If a consumer's queue fills up (consumer is slow or disconnected), subsequent events for that subscriber are dropped.

### The Async Iterator (Subscription)

When a consumer calls `bus.on_chat(42)` or `bus.subscribe(source="chat:42")`, they receive an `AsyncIterator[CoreEvent]`:

```python
async def _iterate(sub: _Subscription) -> AsyncIterator[CoreEvent]:
    try:
        while True:
            event = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
            if event is None:
                return                            # shutdown signal
            if sub.is_end(event):
                yield event                      # deliver STREAM_END
                return                            # then terminate
            yield event                          # deliver normal event
    finally:
        self._unsubscribe(sub)                   # cleanup on exit
```

Key behaviors:

- **Timeout polling**: Uses 1-second timeout on queue get to allow periodic checks even when the queue is empty
- **STREAM_END delivery**: The subscriber receives the `STREAM_END` event, then the iterator terminates (allowing the SSE response to close gracefully)
- **Auto-cleanup**: When the iterator exits (normally or via break), `_unsubscribe` removes the subscription from the bus
- **Shutdown sentinel**: `bus.shutdown()` puts `None` into all queues; the iterator sees `None` and returns without yielding

## Source Routing

Sources are string identifiers with a typed prefix:

```python
def chat_source(session_id: int) -> str:   # -> "chat:42"
def workflow_source(job_id: int) -> str    # -> "workflow:7"
```

This naming convention lets wildcard subscribers (`source=None`) filter by source prefix if needed, and keeps the routing scheme consistent across all producers.

## Convenience Methods

Rather than constructing raw `CoreEvent` objects, producers use typed helper methods:

| Method | Use |
|--------|-----|
| `emit_chat(session_id, event_type, data)` | Publish an agent event |
| `emit_workflow(job_id, event_type, data)` | Publish a workflow step event |
| `end_chat_stream(session_id)` | Signal end of chat stream |
| `end_workflow_stream(job_id)` | Signal end of workflow stream |
| `on_chat(session_id)` | Subscribe to all events for a chat session |
| `on_workflow(job_id)` | Subscribe to all events for a workflow job |

## Usage Patterns

### Producer: Agent Engine

The agent engine publishes events during `step()`. Callbacks are wired once at the start of `run()` and fire asynchronously as the agent produces output:

```python
async def content_cb(chunk: str):
    await event_bus.emit_chat(
        session_id,
        CoreEventType.AGENT_CONTENT,
        {"chunk": chunk},
    )

await agent.step(
    input=user_input,
    stream=True,
    content_chunk_callbacks=[content_cb],
    ...
)
```

At the end of `run()`, a `finally` block ensures `STREAM_END` is always emitted, even on error:

```python
try:
    await agent.step(...)
    # ... persist messages, update clipboard, broadcast token usage
finally:
    await event_bus.end_chat_stream(session_id)
```

### Producer: Workflow Engine

Step callbacks translate `WorkflowEvent` (internal schema) into `CoreEvent` (bus protocol):

```python
async def step_start_cb(event: WorkflowEvent):
    await event_bus.emit_workflow(
        resolved_job_id,
        CoreEventType.WORKFLOW_STEP_START,
        {"step_id": event.step_id, "message": event.message},
    )

# wrapped_cb routes STEP_START → step_start_cb, etc.
step_callbacks = [wrapped_cb]

output = await self._run(manifest, inputs, step_callbacks=step_callbacks)
```

`STREAM_END` is emitted in `finally`:

```python
try:
    output = await self._run(manifest, inputs, step_callbacks=step_callbacks)
    self.workflow_job_manager.mark_completed(resolved_job_id, user_id, output)
except Exception as e:
    self.workflow_job_manager.mark_failed(resolved_job_id, user_id, str(e))
    raise
finally:
    await event_bus.end_workflow_stream(resolved_job_id)
```

### Consumer: SSE Router

FastAPI routers subscribe to the bus and yield SSE-formatted events:

```python
@router.get("/{session_id}/stream")
async def stream_chat(session_id: int, core: CoreDep):
    async def event_generator():
        async for event in core.event_bus.on_chat(session_id):
            if event.event_type == CoreEventType.AGENT_CONTENT:
                yield f"event: content\ndata: {json.dumps({'chunk': event.data.get('chunk', '')})}\n\n"
            elif event.event_type == CoreEventType.AGENT_TOOL_START:
                yield f"event: tool_start\ndata: {json.dumps({'name': event.data.get('name', '')})}\n\n"
            # ...

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

The iterator from `on_chat(session_id)` auto-terminates when it receives `STREAM_END` for that session — no manual cleanup or stream management needed.

### Consumer: Wildcard Subscriber

A subscriber without a source filter receives all events from all producers:

```python
async for event in core.event_bus.subscribe():
    print(f"[{event.source}] {event.event_type.value}: {event.data}")
```

This is used for logging, debugging, or global monitoring.

## Under the Hood: `asyncio.Queue`

Each subscription has its own `asyncio.Queue(maxsize=1024)`. This design gives each subscriber an independent buffer so that a slow consumer on one stream does not block or drop events on another stream.

**Key behaviors of `asyncio.Queue` in this context:**

- `put_nowait`: Non-blocking enqueue; raises `QueueFull` if at capacity — we catch this and drop the event
- `get()`: Blocking deque; returns when an item is available or after timeout
- `get_nowait()` would not work here since we need to wait for events; the 1-second timeout in `_iterate` allows the loop to continue even when the queue is empty

**Queue backpressure**: When a subscriber is slow (e.g., browser tab throttled, network lag), its queue fills up. Subsequent `put_nowait` calls raise `QueueFull` and the event is dropped for that subscriber only. Other subscribers continue normally. The `STREAM_END` signal still gets through when the producer calls `end_chat_stream`/`end_workflow_stream` — it is not dropped by a full queue since the producer keeps trying.

## Limitations

### 1. In-Process Only

The EventBus is entirely in-process. Events cannot cross process boundaries. If the FastAPI server and the agent worker run in separate processes (not the case in `genesis-core`'s current architecture, but possible in scaled deployments), this bus cannot be used as-is — you'd need a distributed message queue (Redis, Kafka, etc.).

### 2. No Persistence

Events are never written to disk. If the process crashes mid-stream, in-flight events are lost. Subscribers that reconnect must fetch current state from the database (e.g., chat history) rather than replaying missed events.

### 3. No Consumer Acknowledgment

Producers fire and forget. There is no mechanism for a consumer to say "I have processed event #42, you can discard it." This means:
- A slow consumer sees only the latest events; gaps indicate it fell behind
- Events are not re-delivered on subscriber reconnection

### 4. Queue Overflow Drops Events Silently

When `sub.queue.put_nowait()` raises `QueueFull`, the event is silently dropped. This is intentional to prevent a slow subscriber from back-pressuring the entire bus. However, it means:
- Producers have no feedback that a subscriber is overwhelmed
- You cannot distinguish "subscriber is slow" from "subscriber disconnected" without additional monitoring

### 5. No Message Ordering Across Subscribers

Each subscriber receives events in the order they were published **individually** — but if subscriber A is slow and subscriber B is fast, B may be well ahead of A on the same source. This is inherent in the per-subscription-queue design and is by design (isolation), but it means you cannot use the EventBus to coordinate ordering across consumers.

### 6. STREAM_END Is Best-Effort on Queue Overflow

If a subscriber's queue is full when `STREAM_END` is published, `put_nowait` will also raise `QueueFull`, and the termination signal is also dropped. The subscriber's iterator will hang until the next `put_nowait` succeeds or the timeout fires. In practice, with `maxsize=1024`, a subscriber getting `STREAM_END` dropped means it received at least 1023 other events — at which point the stream is effectively complete from the consumer's perspective anyway. But for correctness in low-traffic streams, it is possible for a subscriber to miss `STREAM_END` if its queue was full before it arrived.

### 7. Single-Node Only

There is no mechanism for multiple GenesisCore instances on different machines to share subscriptions or coordinate. Each process has its own `EventBus` with its own subscription list. SSE connections are sticky to the specific server process that handles them.

## When to Use `publish()` vs Convenience Methods

**Use convenience methods** (`emit_chat`, `emit_workflow`) when publishing events that naturally belong to a chat session or workflow job. They construct the correct `source` string automatically.

**Use `publish()` directly** when the event does not naturally map to a single source (e.g., a system-wide log event, or an event that spans multiple sources), or when you need fine-grained control over the `CoreEvent` construction.

## Related Files

| File | Purpose |
|------|---------|
| `genesis-core/src/genesis_core/events.py` | `EventBus`, `CoreEvent`, `CoreEventType`, source helpers |
| `genesis-core/src/genesis_core/core.py` | `GenesisCore.event_bus` — single bus instance per core |
| `genesis-core/src/genesis_core/agent/agent_engine.py` | Producer: emits agent content, reasoning, tool calls, token usage, clipboard snapshots |
| `genesis-core/src/genesis_core/workflow/workflow_engine.py` | Producer: emits workflow step events and `STREAM_END` |
| `genesis-server/src/genesis_server/routers/chat.py` | Consumer: subscribes to `core.event_bus.on_chat(session_id)` for SSE streaming |
| `genesis-server/src/genesis_server/routers/jobs.py` | Consumer: subscribes to `core.event_bus.on_workflow(job_id)` for SSE streaming |
| `genesis-core/tests/test_event_bus.py` | 12 tests covering all subscription patterns, filtering, and cleanup |