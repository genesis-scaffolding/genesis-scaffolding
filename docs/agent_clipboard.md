# Agent Clipboard

The clipboard is the ephemeral working memory of the agent. For high-level context on why it exists, see [agent_loop.md](./agent_loop.md).

## Data model

The clipboard is a Pydantic model with five distinct data channels. All channels except `user_profile_content` have a time-to-live (TTL) that counts down each turn.

### AgentClipboardFile

Tracks files the agent has read or written during the current session.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `Path` | Relative path to the file |
| `current_file_content` | `str` | Most recent file content |
| `previous_file_content` | `str \| None` | Content from the previous step (for diffs) |
| `ttl` | `int` | Turns remaining before removal |
| `is_new` | `bool` | True only on the first step after the file is added |
| `is_edited` | `bool` | True only on the first step after the file is modified |

### AgentClipboardToolResult

Tracks the results of tool calls, separate from the file content.

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of the tool that was called |
| `tool_call_id` | `str` | ID returned by the LLM backend |
| `tool_call_results` | `list[str]` | Result strings from the tool |
| `ttl` | `int` | Turns remaining before removal |

### AgentClipboardTodoItem

Internal todo list maintained by the agent.

| Field | Type | Description |
|-------|------|-------------|
| `completed` | `bool` | Whether the item is done |
| `task_desc` | `str` | Description of the task |

### AgentClipboardPinnedEntity

Tracks productivity and memory entities (tasks, projects, journals, memory events, memory topics) that the agent has pinned from the database.

| Field | Type | Description |
|-------|------|-------------|
| `item_type` | `Literal` | One of task, project, journal, memory_event, memory_topic |
| `item_id` | `int` | Database ID of the entity |
| `resolution` | `Literal["summary", "detail"]` | How much data to show |
| `ttl` | `int` | Turns remaining before removal |
| `data` | `dict[str, Any]` | Serialized entity data, refreshed every turn via live-sync |

The `data` field is a dictionary snapshot of the entity. It is refreshed every turn by `AgentMemory.sync_entities()`, so the agent always sees current state.

### AgentClipboard (aggregate)

The root model containing all clipboard channels.

| Field | Type | Description |
|-------|------|-------------|
| `accessed_files` | `dict[str, AgentClipboardFile]` | Keyed by file path string |
| `tool_results` | `dict[str, AgentClipboardToolResult]` | Keyed by tool_call_id |
| `todo_list` | `list[AgentClipboardTodoItem]` | Ordered list |
| `pinned_entities` | `dict[str, AgentClipboardPinnedEntity]` | Keyed by `{item_type}_{item_id}` |
| `memory_tag_hints` | `dict[str, int]` | Tag name to count mapping |
| `user_profile_content` | `str \| None` | Rendered user profile. No TTL. |
| `last_turn_at` | `datetime \| None` | UTC timestamp of the last user message |
| `timezone` | `str` | User timezone string |

## Key methods

### Adding content

`add_file_to_clipboard(file_path, content, ttl)` — adds or updates a file. If the file is new, it sets `is_new=True`. If the file already exists, it stores the previous content in `previous_file_content` and sets `is_edited=True`.

`add_tool_result_to_clipboard(tool_name, tool_call_id, tool_call_results, ttl)` — adds a tool result, keyed by `tool_call_id`.

`pin_entity(item_type, item_id, resolution, ttl)` — adds or updates a pinned entity. If it already exists, only resolution and ttl are updated; the ttl is reset to the new value.

### TTL lifecycle

`reduce_ttl()` — decrements ttl by 1 on all items. Also performs resolution decay: if ttl falls to 5 or below and the resolution is currently `detail`, it is downgraded to `summary`.

`remove_expired_items()` — removes all items where ttl has reached 0. Items with ttl greater than 0 are kept.

`commit()` — clears the `is_new`, `is_edited`, and `previous_file_content` flags on all files. Called once per step after the LLM has processed the clipboard, so flags reflect "fresh" state for only one step.

`forget()` — called by `AgentMemory` at the start of each step. Calls `reduce_ttl()`, then `remove_expired_items()`, then `commit()`.

### Removal

`remove_file_from_clipboard(file_path)` — removes a file from `accessed_files`. Returns True if the file existed.

`remove_dir_from_clipboard(dir_path)` — removes all files under a given directory path.

`get_accessed_files_paths()` — returns a list of all file paths currently in the clipboard.

## TTL and resolution decay

TTL is measured in steps. Every step, `forget()` reduces all TTLs by 1 and removes items at 0.

Resolution decay is a mechanism to reduce token cost as pinned entities age:

```
ttl = 10  ->  detail resolution
ttl <= 5  ->  downgrade to summary
ttl = 0   ->  remove from clipboard
```

The decay is one-way. Once resolution drops to summary it stays there until the item is removed. The agent sees summary data for older pinned items without paying the token cost of detail.

## Render pipeline

`render_to_markdown(shorten=False, timezone="UTC")` converts the clipboard to a markdown string for injection into the LLM context. The output is structured into eight sections, rendered in order:

| Section | Content |
|---------|---------|
| CONVERSATION TIMING | Last exchange timestamp and elapsed time (only if > 60 seconds) |
| AGENT INTERNAL TODO LIST | Checkbox list of todo items |
| USER PRODUCTIVITY SYSTEM (LIVE SYNCED) | Pinned tasks, projects, journals, memory events, memory topics. Grouped by type. Detail content shown only if resolution is `detail` and `shorten=False`. |
| ACCESSED FILES | Lists of new and edited files, then each file with current and previous content |
| TOOL CALL RESULTS | Each tool result, truncated to 50 chars if `shorten=True` |
| MEMORY TAGS | Sorted list of tag names with memory counts |
| USER PROFILE | Rendered profile content, or a prompting message to create one |

Files with `is_new=True` are listed as newly added. Files with `is_edited=True` are listed as recently modified. Full file content is rendered unless `shorten=True`, in which case only the first 50 characters are shown.

The user profile section has no TTL and never expires.

If all sections are empty, `render_to_markdown()` returns the string `"Clipboard is currently empty."`.

## Integration with the agent loop

Tools return a `ToolResult` with four channels that map to clipboard operations:

| ToolResult field | Clipboard action |
|-----------------|-----------------|
| `files_to_add_to_clipboard` | `AgentMemory.add_file_to_clipboard()` |
| `results_to_add_to_clipboard` | `AgentMemory.add_tool_results_to_clipboard()` |
| `entities_to_track` | `AgentMemory.pin_entity()` for each entity |
| `tool_response` | Short string returned to LLM history, not stored in clipboard |

At the start of each step, `AgentMemory.forget()` runs the TTL lifecycle. Then before the LLM call, `AgentMemory.get_clipboard_message()` calls `AgentClipboard.render_to_markdown()` and wraps the result in a system message. This system message is injected into the LLM context by `Agent._inject_clipboard()`.

See [agent_loop.md](./agent_loop.md) for how this fits into the full step loop.