# Chat SSE Streaming

## Overview

This document describes the end-to-end data flow for chat interactions. A user's message travels from the frontend through the FastAPI server into the agent core, and back through Server-Sent Events (SSE) for real-time display. The callback system bridges the agent's internal execution to external consumers.

## Component Map

| Component | Module |
|-----------|--------|
| ChatManager / ActiveRun | `genesis_server.chat_manager` |
| Chat router | `genesis_server.routers.chat` |
| Callback type definitions | `genesis_core.schemas` |

## Callback System

The agent communicates with external consumers through four callback types, defined in `genesis_core/schemas.py`:

- `StreamCallback` — For content and reasoning chunks
- `ToolCallback` — For `tool_start` and `tool_result` events; receives `(tool_name, tool_args_or_result)`

These callbacks are passed into the `Agent` constructor and invoked during `step()` execution. They are invoked synchronously during each turn.

## ChatManager and ActiveRun

`ChatManager` is an app-level singleton holding `ActiveRun` instances per session. Each `ActiveRun` manages the state of an in-progress agent execution and maintains a list of `asyncio.Queue` instances — one per connected SSE client.

### ActiveRun Methods

| Method | Purpose |
|--------|---------|
| `handle_content` | Appends text chunk to the last assistant message, broadcasts to all clients |
| `handle_reasoning` | Appends reasoning chunk, broadcasts to all clients |
| `handle_tool_start` | Adds a `tool_calls` entry with `status='running'`, broadcasts `tool_start` |
| `handle_tool_result` | Marks tool as completed, replaces index with full tool message, broadcasts `tool_result` |
| `handle_clipboard` | Broadcasts the current clipboard markdown to all clients after an agent step |

### Broadcasting

Each `handle_*` method internally calls `_broadcast(event, payload, index)` which puts the payload into every connected client's queue. All connected SSE clients receive the same events simultaneously.

## Chat Router Endpoints

### POST `/chats/{session_id}/message`

Initiates an agent run:

1. Validates the session and checks `is_running` concurrency lock
2. Reconstructs `AgentMemory` from database messages + clipboard state
3. Gets or creates an `ActiveRun` from `ChatManager`
4. Binds the ActiveRun's handlers directly as callbacks to `agent.step()`
5. Dispatches `run_agent_task()` to a background task
6. Returns `202 Accepted` immediately

The background task persists new messages to the database and clears `is_running` after the agent completes.

### GET `/chats/{session_id}/stream`

Streams SSE events to the frontend:

1. On connect, sends a **catchup** event containing all interim messages accumulated so far
2. Then loops, waiting on the client's queue and yielding SSE events
3. Cleans up the client queue on disconnect

## SSE Event Reference

All events share a `_broadcast` envelope: `{event: string, data: Any, index: number | null}`. Frontend handlers must unwrap `parsed.data` for events carrying objects (not primitives).

| Event | Direction | Broadcast Payload (`parsed.data`) | Effect on Frontend |
|-------|-----------|-----------------------------------|-------------------|
| `catchup` | Server → Client | `{interim_messages: ChatMessage[]}` | Initializes client buffer with all messages so far |
| `content` | Server → Client | `string` (text chunk) | Appends text to `message[index].content` |
| `reasoning` | Server → Client | `string` (reasoning chunk) | Appends text to `message[index].reasoning_content` |
| `tool_start` | Server → Client | `{name: string, args: dict}` | Pushes tool to `message[index].tool_calls` with `status: 'running'` |
| `tool_result` | Server → Client | `{role: 'tool', name: string, content: string}` | Replaces `message[index]` with full tool message |
| `token_usage` | Server → Client | `{history_tokens, clipboard_tokens, total_tokens, max_tokens, percent}` | Updates token usage display in the UI |
| `clipboard` | Server → Client | `{clipboard_md: string}` | Updates clipboard markdown in context |

## Data Flow

```
User sends message → POST /chats/{id}/message
  → Chat router validates session, creates/binds ActiveRun
  → agent.step() called with callbacks
    → LLM call with streaming
    → Callbacks invoked per chunk/turn
      → ActiveRun methods append to messages, _broadcast to all client queues
  → Background task persists messages to DB after step completes

SSE clients connected to GET /chats/{id}/stream
  → Receive catchup on connect
  → Receive broadcast events in real-time
```

## Persistence

Message persistence to the database happens exclusively in the background task after `agent.step()` completes. The SSE stream is for real-time display only — it does not write to the database.

## Key Integration Points

**Adding a new SSE event type** requires changes in three layers:

1. **Agent core** (`genesis_core.agent`): Call `agent.get_context_info()` and pass the result to the SSE broadcast at the appropriate point in `run_agent_task()` (e.g., in the `finally` block after DB persistence)
2. **ActiveRun** (`genesis_server.chat_manager`): Add a new `handle_*` method (e.g., `handle_token_usage`) that calls `_broadcast()`
3. **Frontend** (`genesis_frontend`): Add a new `addEventListener` for the event type and update relevant state

For `token_usage` specifically, the broadcast happens in `finally` after DB persistence succeeds, ensuring clients never receive token counts for a failed run.

## Related Modules

- `genesis_server.chat_manager` — `ChatManager` and `ActiveRun` (SSE broadcasting)
- `genesis_server.routers.chat` — Chat router endpoints
- `genesis_core.schemas` — Callback type definitions
