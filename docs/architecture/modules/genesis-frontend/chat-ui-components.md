# Chat UI Components

Components for the real-time chat interface, powered by `ChatProvider` context and Server-Sent Events (SSE). For the full streaming architecture including server-side details, see [genesis-server/sse-streaming.md](../genesis-server/sse-streaming.md).

## Architecture Overview

```
Browser ←→ Next.js ←→ FastAPI (SSE streaming)
```

The chat UI operates in a real-time loop:
1. User sends a message via `ChatInput`
2. `sendChatMessageAction` creates an `ActiveRun` on FastAPI
3. SSE connection streams tokens, tool calls, and reasoning content back to the browser
4. `ChatContext` updates `displayActiveMessages` at 10fps (debounced) while `isRunning`
5. On completion, `refreshHistory()` reloads the full conversation from the database

## ChatProvider Context

**Path:** `components/chat/chat-context.tsx`

The root provider for all chat state. Wrap chat pages with this provider.

```tsx
// In a layout or page
<ChatProvider session={session} initialMessages={messages} initialTokenUsage={tokenUsage}>
  {children}
</ChatProvider>
```

### Context Value

```typescript
interface ChatContextType {
  session: ChatSession;
  messages: ChatMessage[];        // historicalMessages + displayActiveMessages
  sendMessage: (input: string, inputIndex?: number) => Promise<void>;
  isRunning: boolean;
  tokenUsage: TokenUsage | null;
  clipboardMd: string | null;
}
```

`ChatProvider` manages the SSE connection, ephemeral message buffer, and the 10fps throttle interval. It exposes state and handlers to child components via React context. `tokenUsage` and `clipboardMd` are both seeded from the initial GET response and updated on each SSE event.

### Editing a Previous Message

When `inputIndex` is negative, the message is treated as an edit:

```typescript
// Send as edit (inputIndex = -1 means last user message, -2 = second-to-last, etc.)
await sendMessage(newContent, -1);
```

The `inputIndex` maps to user message positions via `userIndices`:

```typescript
const userIndices: number[] = [];
messages.forEach((msg, i) => { if (msg.role === 'user') userIndices.push(i); });
// inputIndex=-1 → userIndices[userIndices.length + (-1)] = last user message
const targetIdx = userIndices[userIndices.length + inputIndex];
```

## MessageList

**Path:** `components/chat/message-list.tsx`

Displays all messages with hover/active state for message actions.

### Active Message State

A single `activeMessageIndex` state controls visibility of buttons and ring highlight:

```typescript
const [activeMessageIndex, setActiveMessageIndex] = useState<number | null>(null);
```

**Behavior:**
- `onMouseEnter` on a message → sets `activeMessageIndex` to that message (if not already set to another)
- `onMouseLeave` on a message → clears `activeMessageIndex` only if it was that message
- `onClick` on a message → toggles: if already active, clears; otherwise sets
- `onClick` on empty space (container) → clears `activeMessageIndex`

```tsx
// Message div
onMouseEnter={() => {
  if (activeMessageIndex !== i) setActiveMessageIndex(i);
}}
onMouseLeave={() => {
  if (activeMessageIndex === i) setActiveMessageIndex(null);
}}
onClick={(e) => {
  e.stopPropagation();
  setActiveMessageIndex(activeMessageIndex === i ? null : i);
}}

// Container
onClick={(e) => {
  if (!e.target.closest('.group')) {
    setActiveMessageIndex(null);
  }
}}
```

### Edit Mode

When `editingIndex === i`, the message renders `InlineEditForm` instead of `MessageBubble`:

```tsx
{editingIndex === i ? (
  <InlineEditForm
    value={editText}
    onConfirm={async (newValue) => {
      const inputIndex = getInputIndex(i, messages);
      await sendMessage(newValue, inputIndex);
      setEditingIndex(null);
    }}
    onCancel={() => {
      setEditingIndex(null);
      setEditText('');
    }}
  />
) : (
  <MessageBubble message={msg} />
)}
```

### getInputIndex

Converts a message index to an `inputIndex` suitable for `sendMessage`:

```typescript
const getInputIndex = (msgIndex: number, messages: ChatMessage[]): number => {
  const userIndices: number[] = [];
  messages.forEach((msg, i) => { if (msg.role === 'user') userIndices.push(i); });
  return userIndices.indexOf(msgIndex) - userIndices.length;
};
// Message at index 5 (a user message, 3rd user message) → inputIndex = 3 - 3 = -3
```

## ChatInput

**Path:** `components/chat/chat-input.tsx`

The message input at the bottom of the chat view.

```typescript
const handleKeyDown = (e: React.KeyboardEvent) => {
  // Submit on Ctrl+Enter or Cmd+Enter
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    handleSubmit();
  }
  // Normal 'Enter' now just creates a new line by default in Textarea
};
```

`TextareaAutosize` from `react-textarea-autosize` auto-resizes the textarea to fit content.

## SSE Event Types

The SSE connection (`/api/chats/${session.id}/stream`) emits these event types:

| Event | Payload | Purpose |
|---|---|---|
| `catchup` | `{ interim_messages: ChatMessage[] }` | Initial sync of in-progress messages |
| `content` | `{ data: string, index: number }` | Appends token to message content |
| `reasoning` | `{ data: string, index: number }` | Appends to `reasoning_content` |
| `tool_start` | `{ name: string, index: number }` | Pushes a new tool call with `status: 'running'` |
| `tool_result` | `{ data: ChatMessage, index: number }` | Replaces message with full tool result |
| `token_usage` | `TokenUsage` | Updates token usage display |
| `clipboard` | `{ data: { clipboard_md: string } }` | Updates clipboard content |

## 10fps Display Debouncer

Direct SSE updates go into `activeRunRef.current` without triggering React re-renders. A `setInterval` running at 10fps reads the ref and updates `displayActiveMessages` state:

```typescript
useEffect(() => {
  if (!isRunning) return;

  const interval = setInterval(() => {
    setDisplayActiveMessages(
      activeRunRef.current
        .filter(Boolean)
        .map(msg => ({
          ...msg,
          tool_calls: Array.isArray(msg.tool_calls) ? [...msg.tool_calls] : undefined
        }))
    );
  }, 100);

  return () => clearInterval(interval);
}, [isRunning]);
```

This throttle balances responsiveness (10 updates per second) with performance (avoids excessive React re-renders during rapid streaming).

## Message Types

| Role | Rendering |
|------|-----------|
| `user` | Right-aligned dark bubble with markdown |
| `assistant` | Markdown content + collapsible reasoning + tool call badges |
| `tool` | Card with tool name and result content |

## Clipboard Panel

The clipboard drawer consists of three components:

- `ClipboardToggleButton` (`components/chat/clipboard-icon.tsx`) — Floating chevron button on the right edge of the chat widget, vertically centered. Only rendered when `showClipboardButton` prop is `true`.
- `ClipboardDrawer` (`components/chat/clipboard-drawer.tsx`) — Slide-out drawer rendered at the widget level. Displays `clipboardMd` as rendered markdown using `react-markdown` + `remark-gfm`.
- `ChatWidget` accepts `showClipboardButton` prop (defaults to `true`) to hide the toggle in compact contexts like the quick chat drawer.

## TokenBar

**Path:** `components/chat/token-bar.tsx`

`TokenBar` is a client component that displays context token usage. It is placed inside `ChatWidget` (which has access to `useChat()`) and renders only when `tokenUsage` is non-null. Use the `chat-viewport-container` CSS class to align the bar horizontally with other chat components.

## Related Modules

- `genesis_frontend/components/chat/chat-context.tsx` — SSE connection, ChatProvider, clipboard state
- `genesis_frontend/components/chat/chat-widget.tsx` — ChatWidget, composes all chat components
- `genesis_frontend/components/chat/token-bar.tsx` — Token display bar
- `genesis_frontend/components/chat/message-bubble.tsx` — Message rendering
- `genesis_frontend/components/chat/clipboard-icon.tsx` — Floating clipboard toggle button
- `genesis_frontend/components/chat/clipboard-drawer.tsx` — Clipboard slide-out drawer
- `genesis_frontend/types/chat.ts` — ChatMessage type definitions