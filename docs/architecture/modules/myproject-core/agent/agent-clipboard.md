# Agent Clipboard

## Overview

The clipboard is a token-optimization layer between the agent and its chat history. Rather than storing every file read and tool result directly in the context window, the clipboard holds them with a TTL and decay policy — keeping the context clean and cheap while still making data available to the agent on demand.

The clipboard replaces naive file reading with intelligent deduplication, automatic expiration, and progressive summarization. This ensures the agent always has access to relevant, current data without overwhelming the context window with redundant or stale information.

## The Problem

Working with an LLM is about getting the right text into the context window to get the right output. Naive agentic reading — storing every file read directly in the chat history — is impractical because:

1. **Sub-optimal reading decisions** — Agents often bring in irrelevant files, read the same file multiple times, or read in small overlapping chunks, wasting tokens.

2. **Accumulation of outdated content** — If an agent modifies a file three times, the chat history contains three slightly different versions of that same file.

3. **Stale pinned entities** — Database entities pinned to clipboard can become stale if not synchronized.

4. **Context rot** — LLMs are stateless; irrelevant files or multiple outdated versions dilutes context and confuses the model.

## The Clipboard Mechanism

The clipboard replaces naive file reading. Key features:

- **Deduplication** — If an agent reads the same file again, the clipboard entry is updated rather than duplicated.
- **TTL (Time To Live)** — Every item has a TTL that decreases every turn. When it hits zero, the item is forgotten.
- **Decay** — As pinned entities age, their resolution downgrades automatically (detail to summary) to save tokens.
- **Live-Sync** — Pinned database entities are refreshed from the database each turn, ensuring the agent always sees current data.
- **Cache Friendly** — Because only appending to message history and not modifying previous messages, prompt caching is preserved.

## Clipboard Content Types

The clipboard tracks seven categories of information:

1. **Todo List** — A list of tasks to keep the agent on track without repeating them in history.

2. **Accessed Files** — A dictionary of file contents keyed by path to prevent duplicates. Tracks both current and previous content to detect edits. Default TTL: 10 turns.

3. **Tool Results** — Results of specific tool calls, kept briefly to allow the agent to reference them. Default TTL: 10 turns.

4. **Pinned Productivity Entities** — Live-synced database records from the user's productivity system (tasks, projects, journals). Pinned by tools via TrackedEntity signals.

5. **Pinned Memory Entities** — Live-synced database records from the agent's memory subsystem (memory events and topics).

6. **System Context** — memory_tag_hints (counts of available semantic tags) and user_profile_content (rendered user profile; never expires via TTL).

7. **Conversation Timing** — Tracks the UTC timestamp of the last user turn (last_turn_at). When rendered to markdown, if more than 60 seconds have elapsed since the last turn, a timing section is included showing when the last exchange occurred and how much time has passed.

## How Tools Pin Entities

Tools signal the agent loop to pin database entities via the ToolResult schema. When a tool (e.g., list_tasks or get_project) returns a ToolResult with entities_to_track populated:

1. Tool execution returns ToolResult with entities_to_track
2. Agent loop detects entities_to_track and calls pin_entity() on each
3. Clipboard creates or updates entry at key {item_type}_{item_id}, resetting TTL
4. Live-sync each turn refreshes entity.data from the database

## TTL and Decay Mechanism

Every turn, forget() is called which:

1. Reduces TTL by 1 for all items
2. Removes items where TTL <= 0
3. Clears is_new/is_edited flags for the next turn

The Decay Rule: When a pinned entity's TTL drops to 5 or below and resolution is "detail", it automatically downgrades to "summary".

TTL Defaults:

- Files: 10 turns
- Tool Results: 10 turns
- Pinned Entities: tool-specified (default 10), decays to summary at TTL<=5
- User Profile: none (never expires)

## Rendering

The clipboard is converted to a Markdown string for injection into the LLM context. Rendered sections in order:

1. Conversation Timing (if more than 60 seconds since last user turn)
2. Agent Internal Todo List
3. User Productivity System (tasks, projects, journals — grouped by type)
4. Tracked Memories (memory events and memory topics)
5. Accessed Files (with status flags: "Recently Added", "Recently Modified")
6. Tool Call Results
7. Memory Tags (semantic tag directory)
8. User Profile (onboarding nudge if absent)

Pinned entities render differently based on resolution:

- summary: ID, title/name, status, key dates
- detail: summary + description, project links, full content

## Related Modules

- `myproject_core.agent.clipboard` — Data models (`AgentClipboard`, `AgentClipboardFile`, `AgentClipboardToolResult`, `AgentClipboardTodoItem`, `AgentClipboardPinnedEntity`)
- `myproject_core.agent.agent_memory` — Clipboard integration (`AgentMemory` wraps `AgentClipboard`, provides `forget()`, TTL decay, entity pin/unpin, live-sync)
