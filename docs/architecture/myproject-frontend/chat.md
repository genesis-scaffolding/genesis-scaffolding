# Chat UI

## Overview

The chat interface communicates with the FastAPI backend via a Server-Sent Events (SSE) connection to receive real-time agent output. For the full streaming architecture including server-side details, see [myproject-server/sse-streaming.md](../myproject-server/sse-streaming.md).

## SSE Connection

The `ChatProvider` establishes an SSE connection whenever the agent is running:

```typescript
const eventSource = new EventSource(`/api/chats/${session.id}/stream`);
```

## SSE Events

| Event | Frontend Action |
|-------|----------------|
| `catchup` | Initialize the ephemeral message buffer with all interim messages accumulated so far |
| `content` | Append text to `message[index].content` |
| `reasoning` | Append text to `message[index].reasoning_content` |
| `tool_start` | Push tool to `message[index].tool_calls` with `status: 'running'` |
| `tool_result` | Update tool status to completed, replace message index with full tool message |
| `token_usage` | Update `tokenUsage` state with context breakdown (`history_tokens`, `clipboard_tokens`, `total_tokens`, `max_tokens`, `percent`) |

## 10fps Display Throttle

Direct SSE updates go into `activeRunRef.current` without triggering React re-renders. A `setInterval` running at 10fps reads the ref and updates `displayActiveMessages` state:

```typescript
const interval = setInterval(() => {
    setDisplayActiveMessages(activeRunRef.current.filter(Boolean).map(msg => ({
        ...msg,
        tool_calls: Array.isArray(msg.tool_calls) ? [...msg.tool_calls] : undefined
    })));
}, 100);
```

This throttle balances responsiveness (10 updates per second) with performance (avoids excessive React re-renders during rapid streaming).

## Message Types

| Role | Rendering |
|------|-----------|
| `user` | Right-aligned dark bubble with markdown |
| `assistant` | Markdown content + collapsible reasoning + tool call badges |
| `tool` | Card with tool name and result content |

## ChatProvider

`ChatProvider` (`components/chat/chat-context.tsx`) manages the SSE connection, ephemeral message buffer, and the 10fps throttle interval. It exposes state and handlers to child components via React context. It also holds `tokenUsage` state, seeded from the initial GET response and updated on each `token_usage` SSE event.

## TokenBar

`TokenBar` (`components/chat/token-bar.tsx`) is a client component that displays context token usage. It is placed inside `ChatWidget` (which has access to `useChat()`) and renders only when `tokenUsage` is non-null. Use the `chat-viewport-container` CSS class to align the bar horizontally with other chat components.

## Related Modules

- `myproject_frontend/components/chat/chat-context.tsx` — SSE connection and ChatProvider
- `myproject_frontend/components/chat/chat-widget.tsx` — ChatWidget, renders TokenBar
- `myproject_frontend/components/chat/token-bar.tsx` — Token display bar
- `myproject_frontend/components/chat/message-bubble.tsx` — Message rendering
- `myproject_frontend/types/chat.ts` — ChatMessage type definitions
