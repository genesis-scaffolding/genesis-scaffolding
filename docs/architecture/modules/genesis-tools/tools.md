# Agent Tools

## Overview

Agent tools are Python functions callable by the LLM via function-calling schema (OpenAI tool format). Each tool is a class inheriting from `BaseTool`, with a name, description, JSON Schema parameters, and an async `run()` method. The agent uses the `ToolRegistry` to enumerate available tools and execute them.

## BaseTool ABC

Every agent tool inherits from `BaseTool`, an abstract base class that defines the contract:

- **`name`**: Unique identifier; used in function-calling schema sent to the LLM
- **`description`**: Human-readable description that helps the LLM decide when to call the tool
- **`parameters`**: JSON Schema describing the tool's input arguments (OpenAI function-call format)
- **`run()`**: Async method that executes the tool logic and returns a `ToolResult`

## ToolRegistry

`ToolRegistry` is a global registry mapping tool names to class implementations. The agent queries it to:
- Retrieve tool schemas → sent to the LLM as function-calling capabilities
- Instantiate and execute tools at runtime

## ToolResult Multi-Channel Output

Tools return a `ToolResult` with four independent output channels:

| Channel | Purpose |
|---|---|
| `tool_response` | Text returned to the LLM chat history |
| `results_to_add_to_clipboard` | Large text kept out of the LLM context (preserves context window) |
| `files_to_add_to_clipboard` | Files read and available on the next agent turn |
| `entities_to_track` | DB entities (tasks, projects, journals, memories) pinned to clipboard for live-sync |

The multi-channel design means a single tool call can: return text to the LLM, add a large result to the clipboard (not history), read a file for next turn, and pin a DB entity — all simultaneously.

## Sandbox Contract

All file paths are resolved relative to the sandbox working directory. The sandbox boundary is enforced by `_validate_path()` — tools must call it before any file operation. Path traversal attacks (`../etc/passwd`) are blocked by checking the resolved path stays within the sandbox root.

`_validate_path()` supports `create_if_missing=True` to auto-create directories when needed (e.g., download directories for web tools). This only applies when `should_be_dir=True`.

## Tool Categories

Built-in tools (~30 total) across 5 categories:

| Category | Tools | Purpose |
|---|---|---|
| **File Operations** | read, write, edit, delete, move, search files, list dirs | Sandbox filesystem access |
| **Web** | web search, news search, RSS fetch, web page fetch | External data retrieval |
| **Productivity** | CRUD for tasks, projects, journals | User productivity data |
| **Memory** | EventLog and TopicalMemory CRUD, FTS search | Agent persistent memory |
| **Utilities** | date computation, FTS index rebuild | Helper utilities |

## Schema Translation

Tool schemas are defined in OpenAI format (JSON Schema with `parameters`). The LLM client automatically translates them to Anthropic format when calling Anthropic-compatible providers, and vice versa. This is handled transparently in `genesis_core.llm` — tools authors do not need to write provider-specific schemas.

## Clipboard Integration

The `entities_to_track` channel in `ToolResult` pins database entities to the agent's clipboard for live-sync across turns. See [agent-clipboard.md](../genesis-core/agent/agent-clipboard.md) for full details on how pinning works, TTL decay, and resolution levels (detail vs summary).

## Related Modules

- `genesis_core.tools.base` — `BaseTool` abstract base class
- `genesis_core.tools.registry` — `ToolRegistry` global registry
- `genesis_core.tools` — Tool implementations by category
