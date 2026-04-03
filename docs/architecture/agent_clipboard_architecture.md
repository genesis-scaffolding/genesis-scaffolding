# Agent Clipboard Architecture

One of the experimental optimizations in this project is a feature called the **"clipboard."** The goal is to optimize the number of tokens an LLM agent uses. Lower token consumption means the agent can maintain coherence over longer sessions without hitting context limits.

## The Problem: How Agents Handle Context

Working with an LLM is basically about getting the "right" text into the context window to get the "right" output. When an agent needs to summarize or compare documents, those documents have to be stuffed into the context somehow.

In an "agentic" approach, the LLM calls a tool to request a file. While this is the most flexible method, it's often inefficient for a few reasons:

### 1. Sub-optimal reading decisions
Agents often make mistakes about what to read. For example, if you ask an agent to create a React component based on a backend Pydantic model, it needs to see the model, the utility code, and some existing components for reference.

If you did this manually, you'd paste exactly those files and use a few thousand tokens. An agent, however, might:
*   Bring in irrelevant files because it misunderstood the directory structure.
*   Read the same file multiple times if a previous edit failed.
*   Read a file in small, overlapping chunks, wasting tokens on redundant text.

This "gunk" builds up. Suddenly, a 128k context window isn't enough for a task that should only require a few thousand tokens.

### 2. Accumulation of outdated content
If an agent modifies a file three times, the chat history often ends up containing three slightly different versions of that same file. This is a massive waste of space.

### 3. Stale pinned entities
When tools pin database entities (tasks, projects, memories) to the clipboard, the data can become stale if not synchronized. An agent acting on outdated task status or project details can make poor decisions.

### 4. Misleading the models
We tend to think of agents as having a "memory" of the past, but LLMs are stateless. Every time you wake them up, they see the entire history as one long string. Irrelevant files or multiple outdated versions of the same code dilutes the context and confuses the model, leading to "context rot" and lower performance.

**Summary:** Naive agentic reading (storing every file read directly in the chat history) is impractical. It requires expensive SOTA models to handle the mess, whereas a cleaner context could be handled by smaller, faster models.

---

## The Clipboard Mechanism

The clipboard is designed to replace naive file reading. It aims to:
*   Stop the accumulation of outdated/duplicate content.
*   Automatically "forget" unused information via TTL and decay.
*   Keep tool call sequences compatible with LLM providers.
*   **Preserve prompt caching** (prefix caching), which keeps the agent fast and cheap.
*   Provide **live-synced** views of database entities without storing them in chat history.

### How it works
Every agent has a "clipboard"—essentially a bag of data managed by the software harness.

When the agent calls a file-reading tool, the content doesn't go into the chat history. Instead, it goes into the **clipboard**. The tool response sent to the LLM is just a "receipt" confirming the file was read.

Before the harness sends a message to the LLM, it injects the current clipboard content as a system message.

**Key features:**
*   **Deduplication:** If an agent reads the same file again, the clipboard entry is updated rather than duplicated.
*   **TTL (Time To Live):** Every item on the clipboard has a TTL that decreases every turn. When it hits zero, the item is removed ("forgotten").
*   **Decay:** As pinned entities age, their resolution downgrades automatically (detail → summary) to save tokens.
*   **Live-Sync:** Pinned database entities are refreshed from the database each turn, ensuring the agent always sees current data.
*   **Cache Friendly:** Because we only append to the message history and don't modify previous messages, we don't break the LLM provider's prompt caching.

---

## Clipboard Content Types

The clipboard tracks six categories of information:

### 1. Todo List
A list of tasks to keep the agent on track without repeating them in history.

```python
class AgentClipboardTodoItem(BaseModel):
    completed: bool = False
    task_desc: str
```

### 2. Accessed Files
A dictionary of file contents, keyed by path to prevent duplicates. Tracks both current and previous content to detect edits.

```python
class AgentClipboardFile(BaseModel):
    file_path: Path
    current_file_content: str
    previous_file_content: str | None = None
    ttl: int = 10  # Default: survives 10 turns
    is_new: bool = False    # Just added this turn?
    is_edited: bool = False  # Modified this turn?
```

### 3. Tool Results
Results of specific tool calls, kept briefly to allow the agent to reference them.

```python
class AgentClipboardToolResult(BaseModel):
    tool_name: str
    tool_call_id: str
    tool_call_results: list[str]
    ttl: int = 10
```

### 4. Pinned Productivity Entities
Live-synced database records from the user's productivity system (tasks, projects, journals). These are pinned by tools via `TrackedEntity` signals.

```python
class AgentClipboardPinnedEntity(BaseModel):
    item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"]
    item_id: int
    resolution: Literal["summary", "detail"] = "summary"
    ttl: int

    # The actual database record, refreshed each turn via sync_entities()
    data: dict[str, Any] = {}
```

### 5. Pinned Memory Entities
Live-synced database records from the agent's memory subsystem (memory events and topics).

### 6. System Context
- `memory_tag_hints: dict[str, int]` — counts of available semantic tags across all memories
- `user_profile_content: str | None` — rendered user profile; **never expires via TTL**

---

## How Tools Pin Entities to the Clipboard

Tools can signal the agent loop to pin database entities onto the clipboard. This happens via the `ToolResult` schema:

```python
class ToolResult(BaseModel):
    status: Literal["success", "error"]
    tool_response: str
    results_to_add_to_clipboard: list[str] | None = None
    files_to_add_to_clipboard: list[Path] = []
    entities_to_track: list[TrackedEntity] = []  # <-- The pinning signal


class TrackedEntity(BaseModel):
    """A signal from a tool to the Agent Loop to pin a database entity to the clipboard."""
    item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"]
    item_id: int
    resolution: Literal["summary", "detail"] = "summary"
    ttl: int = 10
```

### The Pinning Flow

1. **Tool execution** — a tool (e.g., `list_tasks`, `get_project`) returns a `ToolResult` with `entities_to_track` populated.

2. **Agent loop side-effect** — in `_execute_tool_and_format()` (agent.py:116), the agent detects `entities_to_track` and calls:
   ```python
   self.memory.pin_entity(
       item_type=entity.item_type,
       item_id=entity.item_id,
       resolution=entity.resolution,
       ttl=entity.ttl,
   )
   ```

3. **Clipboard stores or updates** — `AgentClipboard.pin_entity()` creates a new entry or updates an existing one at the same key (`{item_type}_{item_id}`), resetting its TTL.

4. **Live-sync each turn** — at the start of each agent turn, `sync_entities()` is called:
   - Iterates all pinned entities
   - Fetches the latest state from the appropriate database (productivity or memory)
   - Updates `entity.data` with fresh data
   - If the entity was **deleted** from the database, removes it from the clipboard automatically

---

## TTL and Decay Mechanism

Every turn, `AgentMemory.forget()` is called, which:

1. Calls `agent_clipboard.reduce_ttl()` — decrements TTL by 1 for all items
2. Calls `agent_clipboard.remove_expired_items()` — removes items where TTL ≤ 0
3. Calls `agent_clipboard.commit()` — clears `is_new`/`is_edited` flags for the next turn

### The Decay Rule

When a pinned entity's TTL drops to **5 or below**, and its resolution is currently "detail", it **automatically downgrades to "summary"**:

```python
# From schemas.py:reduce_ttl()
if entity.ttl <= 5 and entity.resolution == "detail":
    entity.resolution = "summary"
```

This prevents the agent from receiving token-heavy detail views of entities that have been sitting on the clipboard for a while. The agent still knows about the entity, just in a more compact form.

### TTL Defaults

| Content Type | Default TTL | Notes |
|---|---|---|
| Files | 10 turns | Updated on re-read; previous content stored |
| Tool Results | 10 turns | Cleared after agent references them |
| Pinned Entities | Tool-specified (default 10) | Resets on re-pin; decays to summary at TTL≤5 |
| User Profile | None | Never expires via TTL |

### Expiration

Items with `ttl <= 0` after `reduce_ttl()` are removed from the clipboard in `remove_expired_items()`. This applies to files, tool results, and pinned entities. The user profile is the exception — it renders unconditionally if present, or shows an onboarding nudge if absent.

---

## The Agent Loop and Clipboard Injection

The clipboard is **ephemeral** — it is never stored in `memory.messages`. Each turn:

1. Agent appends the user's input as a message to history
2. `forget()` is called to decay TTLs and remove expired items
3. `remove_deleted_files()` purges files that no longer exist on disk
4. **Clipboard is injected** into the LLM payload via `_inject_clipboard()`
5. LLM responds; tool calls are executed; side-effects update clipboard
6. Only the LLM's response and tool results go into `memory.messages` — the clipboard itself does not

### `_inject_clipboard()` Logic

The clipboard message is injected just before the last user message (or appended if no user message exists). If the last message is a tool response, the clipboard is appended to that tool response content instead.

```python
def _inject_clipboard(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clipboard_msg = self.memory.get_clipboard_message(timezone=self.timezone)

    if history[-1]["role"] == "tool":
        # Append clipboard to last tool result
        tool_result_with_clipboard = history[-1].copy()
        tool_result_with_clipboard["content"] += f"\n\nClipboard context:\n{clipboard_msg['content']}"
        return history[:-1] + [tool_result_with_clipboard]

    # Insert before last user message
    for i in range(len(history) - 1, -1, -1):
        if history[i]["role"] == "user":
            return history[:i] + [clipboard_msg] + history[i:]

    # Fringe case: no user message found
    return history + [clipboard_msg]
```

---

## Live-Sync: Productivity and Memory Entities

Each turn, before calling the LLM, the agent performs three sync operations if the respective database is connected:

### 1. `sync_entities(session, db_type="productivity")`
Refreshes tasks, projects, and journals pinned from the user's productivity database.

### 2. `sync_entities(session, db_type="memory")`
Refreshes memory events and topics pinned from the agent's memory database.

### 3. `sync_memory_tag_hints(session)`
Fetches current tag counts from the memory DB:
```python
counts = memory_service.get_memory_tag_counts(session)
self.agent_clipboard.memory_tag_hints = counts
```

### 4. `sync_user_profile(session)`
Fetches the "user-profile" topical memory and caches its content in the clipboard. This content **never expires via TTL** — it persists until explicitly replaced.

---

## Rendering: `render_to_markdown()`

The clipboard is converted to a Markdown string for injection into the LLM context. The `shorten` flag controls whether full file contents are rendered or just the first 50 characters.

**Rendered sections in order:**
1. Agent Internal Todo List
2. User Productivity System (tasks, projects, journals — grouped by type)
3. Tracked Memories (memory events and memory topics)
4. Accessed Files (with status flags: "Recently Added", "Recently Modified")
5. Tool Call Results
6. Memory Tags (semantic tag directory)
7. User Profile (onboarding nudge if absent)

Pinned entities render differently based on `resolution`:
- **summary**: ID, title/name, status, key dates
- **detail**: summary + description, project links, full content

---

## Schema Reference

```python
class AgentClipboardPinnedEntity(BaseModel):
    item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"]
    item_id: int
    resolution: Literal["summary", "detail"]
    ttl: int
    data: dict[str, Any] = {}  # Live-synced from DB each turn


class AgentClipboard(BaseModel):
    accessed_files: dict[str, AgentClipboardFile] = {}
    tool_results: dict[str, AgentClipboardToolResult] = {}
    todo_list: list[AgentClipboardTodoItem] = []
    pinned_entities: dict[str, AgentClipboardPinnedEntity] = {}
    memory_tag_hints: dict[str, int] = {}  # tag -> count of current memories
    user_profile_content: str | None = None  # Rendered user profile, never TTL-expires
```

---

## Key Files

| File | Purpose |
|---|---|
| `myproject-core/src/myproject_core/schemas.py` | `AgentClipboard`, `AgentClipboardFile`, `AgentClipboardPinnedEntity`, `AgentClipboardToolResult`, `AgentClipboardTodoItem` |
| `myproject-core/src/myproject_core/agent_memory.py` | `AgentMemory` — manages clipboard, TTL, live-sync, rendering |
| `myproject-core/src/myproject_core/agent.py` | `Agent.step()` — orchestrates clipboard injection and tool side-effects |
| `myproject-tools/src/myproject_tools/schema.py` | `ToolResult`, `TrackedEntity` — tool signaling for pinning |
