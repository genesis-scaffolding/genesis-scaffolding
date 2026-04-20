# Implementing a New Tool

This guide explains how to implement a new tool and register it with the global `ToolRegistry`.

## Overview

Tools extend the agent's capabilities. Each tool:

1. Inherits from `BaseTool` ABC
2. Defines `name`, `description`, and `parameters` as class attributes
3. Implements `async run()` returning a `ToolResult`
4. Registers itself with the `ToolRegistry`

## Step 1: Define the Tool Class

Choose a clear `name` and a descriptive `description` — the LLM uses the description to decide when to call the tool. Define `parameters` as a JSON Schema object describing the tool's input arguments.

## Step 2: Design Output Channels

A `ToolResult` has four independent channels. Decide which to use:

| Channel | Use when |
|---|---|
| `tool_response` | Short confirmations, errors, summaries (goes to chat history) |
| `results_to_add_to_clipboard` | Large text the agent should read without cluttering context |
| `files_to_add_to_clipboard` | Files the agent should inspect on the next turn |
| `entities_to_track` | Productivity items (tasks, projects, journals) the agent should monitor |

## Step 3: Implement the Run Method

Key rules:
- **Async only** — use `asyncio.to_thread()` for blocking I/O
- **Always validate paths** — call `_validate_path()` before any file operation
- **Return `ToolResult`**, never raise — errors return `status="error"` with a message

## Step 4: Register the Tool

In `genesis_tools/registry.py`, import the tool class and register it with the registry by name.

## Path Validation Reference

Tools that access the filesystem must validate paths against the sandbox:

```python
self._validate_path(
    working_directory,       # Sandbox root
    path_str,                # Path provided by the agent
    must_exist=True,         # Raise if path does not exist
    should_be_dir=False,     # Raise if path exists but is not a directory
    should_be_file=False,    # Raise if path exists but is not a file
    create_if_missing=False, # Create directory if should_be_dir=True and path missing
)
```

This blocks `../etc/passwd` traversal attacks. It raises `ValueError` if the path escapes the sandbox — the agent loop catches this and returns it as an error `ToolResult`.

**Order of checks:** security validation → auto-create directory (if requested) → existence check → type checks.
