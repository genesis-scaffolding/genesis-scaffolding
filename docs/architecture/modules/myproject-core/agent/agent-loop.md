# Agent Loop

## Overview

The agent loop is the core execution engine that drives the agent's operation. It operates by repeatedly calling the LLM, executing tools, and managing state until a termination condition is reached. Each external call to the agent's step function may consume multiple internal turns before returning, allowing for complex multi-tool workflows to complete within a single observable step of progress.

The loop maintains a clear separation between two distinct operational scopes: a turn represents a single round-trip interaction with the LLM provider, while a step represents the broader unit of observable progress that encompasses one or more turns. This design allows the agent to pursue multi-tool strategies while still providing clean external boundaries for progress tracking.

State management within the loop centers on the clipboard, an ephemeral context layer that is rebuilt fresh for each turn and never persisted to message history. This ephemerality ensures the message history remains append-only, which is essential for maintaining LLM provider prompt caching efficiency. The loop also handles various maintenance operations per-turn including TTL decay, file synchronization, and database entity synchronization.

## Steps vs Turns

Understanding the distinction between steps and turns is fundamental to understanding the agent's execution model.

A turn is one LLM call — a single round-trip where messages are sent to the LLM provider and a response is received. A turn can produce text, tool calls, or both. This is the LLM provider level scope.

A step is one call to the agent's step function — the agent's unit of observable progress. A step consumes 1 to max_turns turns internally, ending when the LLM returns no tool calls (meaning a final response has been reached), or when a termination condition is hit. This is the agent level scope.

| Term | Definition | Scope |
|------|------------|-------|
| **Turn** | One LLM call — a single round-trip where messages are sent to the LLM provider and a response is received. A turn can produce text, tool calls, or both. | LLM provider level |
| **Step** | One call to agent.step() — the agent's unit of observable progress. A step consumes 1 to max_turns turns internally, ending when the LLM returns no tool calls (final response reached), or when a termination condition is hit. | Agent level |

## Loop Flow

Each step call runs through four distinct phases that work together to process user requests and manage the agent's state.

**Prepare Turn** — The loop begins by appending the user message to history. It calls forget() for TTL decay to remove expired clipboard items. Deleted files are removed from the clipboard. Pinned database entities (productivity and memory) are synchronized. Memory tag hints and user profile are also synced at this stage.

**Build Payload** — The loop retrieves messages from memory and injects the clipboard via the clipboard injection mechanism. When the loop reaches max_turns minus 3, it injects a "finalize" warning to nudge the model toward wrapping up its work.

**Call LLM** — The loop streams content chunks to content_chunk_callbacks and reasoning chunks to reasoning_chunk_callbacks. It receives content, reasoning_content, and tool_calls from the LLM response.

**Handle Response** — If no tool_calls are present, the loop stores the assistant message and returns the content. If tool_calls exist, the loop performs a loop detection check, executes tools in parallel, handles side-effects (clipboard updates, pinned entities), stores tool result messages, and loops back to the prepare turn phase.

## What Gets Stored

Only certain data is persisted to the agent's message history. This design keeps the history clean and efficient.

| Data | Stored? | Notes |
|------|---------|-------|
| User messages | Yes | One per step() call |
| Assistant messages | Yes | One per turn that produced a response |
| Tool result messages | Yes | One per tool call |
| Clipboard content | No | Injected each turn as an ephemeral system message |

The clipboard is never stored in message history. It is rebuilt each turn and injected via the clipboard injection mechanism. This keeps the message history append-only, which is essential for LLM provider prompt caching.

## Termination Conditions

A step ends when any of several conditions is met. Understanding these conditions helps explain why the agent might stop mid-workflow.

**LLM returns no tool calls** — This is the most common happy path. When the LLM produces a final text response with no tool calls, the step is complete.

**Max turns reached** — Each step has a configurable max_turns limit (default: 20). When this limit is reached, the step terminates with a message indicating the limit was reached.

**Loop detected** — The agent detects when the LLM repeatedly makes the exact same set of tool calls with the exact same arguments. Default max_repetitions is 3 — if the same signature appears 3 times consecutively, the step ends. This prevents infinite loops.

**Max turns warning** — At max_turns minus 3, a warning message is injected to nudge the model toward wrapping up. This proactive warning helps prevent abrupt terminations.

## Per-Turn Maintenance

Before each LLM call, several maintenance operations run to keep the agent's state current and clean.

**TTL Decay (forget())** — Every clipboard item has a TTL that decrements by 1 each turn. When TTL reaches 0, the item is removed. For pinned entities, when TTL drops to 5 or below and resolution is "detail", it automatically downgrades to "summary".

**File Synchronization** — Files added to the clipboard are checked against the filesystem each turn. If a file no longer exists, it is removed from the clipboard.

**Database Sync** — Pinned entities (tasks, projects, journals, memory events, memory topics) are live-synced from their respective databases each turn. If a pinned entity was deleted from the database, it is automatically removed from the clipboard.

## Clipboard Injection

The clipboard is injected into the LLM payload as an ephemeral system message — never stored in memory.messages. Injection position follows three rules:

1. If the last message is a tool result, clipboard content is appended to that tool result message.
2. If the last message is a user message, clipboard is inserted just before that user message.
3. If no user or tool message is found, clipboard is appended to the end.

## Tool Side-Effects

When a tool returns a ToolResult, the agent loop handles four potential side-effects:

| Field | Action |
|-------|--------|
| tool_response | Sent back to LLM as a tool result message (stored in memory.messages) |
| files_to_add_to_clipboard | File paths are read, content added to clipboard |
| results_to_add_to_clipboard | Text added to clipboard as tool call results |
| entities_to_track | Entities are pinned to clipboard (key = {item_type}_{item_id}), resetting TTL |

Tool execution itself is parallelized via asyncio.gather(), but the LLM sees them as sequential in the message history.

## Message Format

Messages stored in memory.messages follow the OpenAI tool-call format.

Assistant messages (with tool calls) include:
- role: "assistant"
- content: optional text alongside tool calls
- reasoning_content: if model produces reasoning
- tool_calls: array of {id, type: "function", function: {name, arguments}}

Tool result messages include:
- role: "tool"
- tool_call_id: matches the id from the original tool call
- name: tool name
- content: result text

## Related Modules

- `myproject_core.agent` — Agent loop implementation (`step()`, turn management, loop flow)
- `myproject_core.agent.agent_memory` — Agent memory and clipboard integration (TTL decay via `forget()`, entity pinning)
- `myproject_core.agent.clipboard` — Clipboard data models (`AgentClipboard`, `AgentClipboardFile`, `AgentClipboardPinnedEntity`, `AgentClipboardToolResult`)
