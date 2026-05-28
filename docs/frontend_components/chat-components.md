# Chat Components

## Overview

The chat system is a group of components that render the chat UI, manage session state, and stream real-time updates from the backend via Server-Sent Events (SSE). The system is organized around `ChatProvider`, which holds all session state and drives the SSE connection, and `ChatWidget`, which consumes that state and renders the UI.

## Subcomponent: ChatProvider

### Overview

The central context provider. It wraps the entire chat UI, manages session state, maintains two separate message lists (historical and active), handles the SSE connection, and exposes state via the `useChat` hook. No other component in the chat system manages server communication directly.

### Component Tree

```
ChatProvider (context provider, client component)
├── state: session, historicalMessages, isRunning, tokenUsage, clipboardMd
├── ref: activeRunRef (SSE buffer, not state)
└── renders children with ChatContext value
```

### Props

| Prop | Type | Description |
|---|---|---|
| `session` | `ChatSession` | The active chat session (id, agent_id, is_running, etc.) |
| `initialMessages` | `ChatMessage[]` | Pre-loaded messages — used on page refresh or after SSE ends |
| `initialTokenUsage` | `TokenUsage` \| `undefined` | Pre-loaded context token counts |
| `children` | `React.ReactNode` | The UI components that consume the chat context |

**Usage example:**

```tsx
// In a chat page (server component)
const { session, messages, tokenUsage } = await getChatPageData(sessionId);

<ChatProvider
  session={session}
  initialMessages={messages}
  initialTokenUsage={tokenUsage}
>
  <ChatWidget />
</ChatProvider>
```

The page is a server component. It fetches initial data and passes it to `ChatProvider`. All subsequent state management is client-side inside the provider.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `session` | `ChatSession` | Active session (can be updated if needed) |
| `historicalMessages` | `ChatMessage[]` | Messages persisted to the database |
| `isRunning` | `boolean` | Whether an SSE stream is currently active |
| `tokenUsage` | `TokenUsage \| null` | Context token counts |
| `clipboardMd` | `string \| null` | Agent clipboard content |

**Refs (not state, no re-renders):**

| Ref | Type | Purpose |
|---|---|---|
| `activeRunRef` | `ChatMessage[]` | SSE buffer — accumulates streaming messages without triggering re-renders |
| `displayActiveMessages` | `ChatMessage[]` | State copy of the ref, updated at 10fps via interval |

### Internal Operations

**Dual Message Lists**

There are two separate message stores:

1. `historicalMessages` — messages already saved to the database (loaded on page open, refreshed after SSE ends)
2. `displayActiveMessages` — messages being streamed in real-time during an active run

The consumer sees the combined list:

```typescript
const allMessages = [...historicalMessages, ...displayActiveMessages];
```

This separation allows the UI to render live streaming content without mutating the historical record. When SSE ends, `refreshHistory()` copies the final active run into historical and clears the active buffer.

**SSE Connection**

The SSE effect runs only when `isRunning` is true:

```typescript
useEffect(() => {
  if (!isRunning) return;

  const eventSource = new EventSource(`/api/chats/${session.id}/stream`);

  eventSource.addEventListener('catchup', (e) => {
    activeRunRef.current = e.data.interim_messages;
  });

  eventSource.addEventListener('content', (e) => {
    const { data, index } = JSON.parse(e.data);
    if (!activeRunRef.current[index]) {
      activeRunRef.current[index] = { role: 'assistant', content: '' };
    }
    activeRunRef.current[index].content += data;
  });

  eventSource.addEventListener('reasoning', (e) => {
    const { data, index } = JSON.parse(e.data);
    if (!activeRunRef.current[index]) {
      activeRunRef.current[index] = { role: 'assistant', content: '', reasoning_content: '' };
    }
    activeRunRef.current[index].reasoning_content =
      (activeRunRef.current[index].reasoning_content || "") + data;
  });

  eventSource.addEventListener('tool_start', (e) => {
    const { data, index } = JSON.parse(e.data);
    activeRunRef.current[index].tool_calls.push({ ...data, status: 'running' });
  });

  eventSource.addEventListener('tool_result', (e) => {
    const { data, index } = JSON.parse(e.data);
    activeRunRef.current[index] = data;
  });

  eventSource.addEventListener('token_usage', (e) => setTokenUsage(e.data));
  eventSource.addEventListener('clipboard', (e) => setClipboardMd(e.data.clipboard_md));

  eventSource.onerror = () => {
    eventSource.close();
    setIsRunning(false);
    refreshHistory();
  };
}, [isRunning, session.id]);
```

**SSE Events Reference**

| Event | Payload | Effect |
|---|---|---|
| `catchup` | `{ interim_messages: ChatMessage[] }` | Initialize active run buffer from current server state |
| `content` | `{ data: string, index: number }` | Append token to message content |
| `reasoning` | `{ data: string, index: number }` | Append to reasoning_content |
| `tool_start` | `{ name, arguments, index }` | Add running tool call badge |
| `tool_result` | `ChatMessage (status: completed)` | Replace message with full tool result |
| `token_usage` | `TokenUsage` | Update token bar display |
| `clipboard` | `{ clipboard_md: string }` | Update clipboard drawer content |

**10fps Display Debouncer**

SSE events arrive at high frequency. A 100ms interval polls the active run buffer and updates `displayActiveMessages`:

```typescript
useEffect(() => {
  if (!isRunning) return;
  const interval = setInterval(() => {
    setDisplayActiveMessages(activeRunRef.current.filter(Boolean).map(msg => ({ ...msg })));
  }, 100);
  return () => clearInterval(interval);
}, [isRunning]);
```

Without this, every SSE event would trigger a React re-render, which would be excessive for high-frequency token streams.

**sendMessage**

```typescript
const sendMessage = async (input: string, inputIndex?: number) => {
  if (isRunning) return;

  activeRunRef.current = [{ role: 'user', content: input }];
  setDisplayActiveMessages([...activeRunRef.current]);

  await sendChatMessageAction(session.id, input, inputIndex);
  setIsRunning(true);
};
```

`inputIndex` is used for message editing. When negative, the backend truncates history at that user message and re-runs the turn.

**refreshHistory**

Called when SSE ends (on error or close):

```typescript
const refreshHistory = async () => {
  const data = await getChatHistoryAction(session.id);
  setHistoricalMessages(data.messages.map(m => m.payload));
  activeRunRef.current = [];
  setDisplayActiveMessages([]);
};
```

This reloads the final message list from the database, ensuring the UI reflects any corrections or tool results the backend recorded.

### Key Files

- `components/chat/chat-context.tsx` — ChatProvider, useChat hook
- `app/actions/chat.ts` — `sendChatMessageAction`, `getChatHistoryAction`

---

## Subcomponent: ChatWidget

### Overview

The root consumer of `ChatProvider`. It renders the token bar, message list, chat input, and optionally the clipboard drawer. It does not manage any server-facing state — it reads everything from `useChat()`.

### Component Tree

```
ChatWidget
├── <TokenBar>  (token usage display, only rendered if tokenUsage exists)
├── <MessageList>  (scrollable message history)
├── <ChatInput>  (text input with submit button)
├── <ClipboardToggleButton>  (only if showClipboardButton=true)
└── <ClipboardDrawer>  (only if showClipboardButton=true)
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `showClipboardButton` | `boolean` | `true` | Whether to show the clipboard toggle button and drawer |

**Usage example:**

```tsx
// Default (shows clipboard button)
<ChatWidget />

// Quick chat — clipboard is managed by the quick chat context, hide the button
<ChatWidget showClipboardButton={false} />
```

### Internal State

| State | Type | Purpose |
|---|---|---|
| `isClipboardOpen` | `boolean` | Controls whether ClipboardDrawer is visible |

### Key Files

- `components/chat/chat-widget.tsx`

---

## Subcomponent: MessageList

### Overview

Renders the combined message list. Handles auto-scroll to the latest message, user scroll-up detection (pauses auto-scroll when the user scrolls up to read older messages), copy-to-clipboard, and message editing.

### Component Tree

```
MessageList (memoized)
├── <scroll container>  (flex-1 min-h-0 overflow-y-auto, handles scroll detection)
│   └── <content wrapper>  (chat-viewport-container, max-w-4xl)
│        └── <MessageBubble> per message (with copy/edit buttons on hover)
└── <scroll anchor>  (invisible div at bottom, scrollIntoView target)
```

### Props

| Prop | Type | Description |
|---|---|---|
| `messages` | `ChatMessage[]` | Combined list from `useChat()` |

### Internal State

| State | Type | Purpose |
|---|---|---|
| `copiedIndex` | `number \| null` | Which message index shows "Copied!" feedback |
| `activeMessageIndex` | `number \| null` | Which message is being hovered (shows action buttons) |
| `editingIndex` | `number \| null` | Which message is in edit mode (renders InlineEditForm) |
| `editText` | `string` | Current text in the edit form |

**Refs:**

| Ref | Type | Purpose |
|---|---|---|
| `userScrolledUpRef` | `boolean` | Tracks if user has manually scrolled away from bottom |
| `lastMessageCountRef` | `number` | Previous message count (detects new messages) |

### Internal Operations

**Auto-scroll Logic**

```typescript
const userScrolledUpRef = useRef(false);

const handleScroll = () => {
  const distanceFromBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight;
  userScrolledUpRef.current = distanceFromBottom > 50;
};

useEffect(() => {
  if (userScrolledUpRef.current) return;
  scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages]);
```

The ref is reset when a new user message arrives (detected by comparing `messages.length` with `lastMessageCountRef`), so the UI auto-scrolls after each user prompt but not when the agent is generating.

**Edit Flow**

1. User hovers a message and clicks "Edit"
2. `editingIndex` is set, `editText` is populated with message content
3. `InlineEditForm` renders in place of `MessageBubble`
4. On confirm, `sendMessage(newValue, inputIndex)` is called
5. `inputIndex` is calculated: find all user message indices, negate the count minus the current index

```typescript
const getInputIndex = (msgIndex: number, messages: ChatMessage[]): number => {
  const userIndices: number[] = [];
  messages.forEach((msg, i) => { if (msg.role === 'user') userIndices.push(i); });
  return userIndices.indexOf(msgIndex) - userIndices.length;
};
```

### Key Files

- `components/chat/message-list.tsx`

---

## Subcomponent: MessageBubble

### Overview

Renders a single message. Different styling for user (dark bubble, right-aligned), assistant (left-aligned, reasoning accordion, markdown), and tool (card with monospace pre block) roles. System messages are not rendered.

### Component Tree

```
MessageBubble (memoized with custom comparison)
├── <user mode>
│     └── <div> bg-[#2f2f2f] text-white, right-aligned
│          └── MarkdownText (inverted)
├── <assistant mode>
│     ├── <Accordion> (reasoning, collapsible)
│     ├── MarkdownText (content)
│     └── <tool call badges> (running: spinner, completed: check icon)
├── <tool mode>
│     └── <Card> with tool name header and monospace pre block
└── <system mode> → returns null
```

### Props

| Prop | Type | Description |
|---|---|---|
| `message` | `ChatMessage` | The message object to render |

### Internal Operations

**Custom Memoization**

MessageBubble uses a custom comparison function to avoid re-renders when content has not changed:

```typescript
export const MessageBubble = memo(({ message }: { message: ChatMessage }) => {
  // ...
}, (prev, next) =>
  prev.message.content === next.message.content &&
  prev.message.reasoning_content === next.message.reasoning_content &&
  prev.message.tool_calls?.length === next.message.tool_calls?.length &&
  prev.message.tool_calls?.[prev.message.tool_calls.length - 1]?.status ===
  next.message.tool_calls?.[next.message.tool_calls.length - 1]?.status
);
```

This prevents parent state changes from cascading into every message bubble re-render.

### Key Files

- `components/chat/message-bubble.tsx`
- `components/ui/markdown-text.tsx` — rendered content

---

## Subcomponent: ChatInput

### Overview

A textarea-based input with auto-grow, submit on Ctrl/Cmd+Enter, and a send button that reflects the running state. Reads `sendMessage` and `isRunning` from `useChat()`.

### Component Tree

```
ChatInput (client component)
└── <container> (rounded-2xl, border, focus ring)
      ├── <TextareaAutosize> (auto-grow, 44px min, 60px max)
      └── <Button> (send icon, or spinner when isRunning)
```

### Props

No props — reads state directly from `useChat()`.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `input` | `string` | Current input text |

### Internal Operations

**Auto-grow Textarea**

Uses `react-textarea-autosize` with `maxRows={10}`. The textarea grows with content up to 10 rows, then scrolls internally.

**Submit on Modifier+Enter**

```typescript
const handleKeyDown = (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    handleSubmit();
  }
};
```

Normal Enter creates a new line. Ctrl/Cmd+Enter submits.

### Key Files

- `components/chat/chat-input.tsx`

---

## Subcomponent: QuickChatSheet

### Overview

A sheet wrapper that initializes a quick chat session when opened and mounts `ChatProvider` with the session data. Used from `FloatingActionMenu` to open a chat panel without navigating away from the current page.

### Component Tree

```
QuickChatSheet (Sheet wrapper)
├── <SheetContent> (side="right", no auto close button)
│     ├── <SheetTitle> with session number
│     ├── <Maximize2 button> (Link to full chat page)
│     └── (conditional rendering)
│          ├── <Loader2> (while loading session)
│          ├── <error message> (if failed)
│          └── <ChatProvider> + <ChatWidget> (when session loaded)
```

### Props

| Prop | Type | Description |
|---|---|---|
| `open` | `boolean` | Controls whether the sheet is visible |
| `onOpenChange` | `(open: boolean) => void` | Called when the user closes the sheet or presses escape |

**Usage example:**

```tsx
const [quickChatOpen, setQuickChatOpen] = useState(false);

<QuickChatSheet open={quickChatOpen} onOpenChange={setQuickChatOpen} />
```

### Internal State

| State | Type | Purpose |
|---|---|---|
| `session` | `ChatSession \| null` | Loaded from `openQuickChatAction` |
| `messages` | `ChatMessage[]` | Loaded from `openQuickChatAction` |
| `tokenUsage` | `TokenUsage \| undefined` | Loaded from `openQuickChatAction` |
| `loading` | `boolean` | True while session is being fetched |
| `error` | `string \| null` | Error message if session load failed |

### Internal Operations

**Session Initialization**

Every time `open` becomes `true`, the effect resets state and fetches a fresh session:

```typescript
useEffect(() => {
  if (!open) return;

  setLoading(true);
  setError(null);
  setSession(null);
  setMessages([]);
  setTokenUsage(undefined);

  openQuickChatAction()
    .then(data => {
      setSession(data.session);
      setMessages(data.messages);
      setTokenUsage(data.context_tokens);
    })
    .catch(err => {
      setError(err.message);
    })
    .finally(() => {
      setLoading(false);
    });
}, [open]);
```

`openQuickChatAction` creates a new quick chat session or returns the existing one on the server.

### Key Files

- `components/dashboard/quick-chat-sheet.tsx`
- `app/actions/quick-chat.ts` — `openQuickChatAction`