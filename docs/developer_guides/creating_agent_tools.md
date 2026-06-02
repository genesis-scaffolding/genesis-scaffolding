# Creating Agent Tools

This guide walks you through implementing a new tool for the agent system.

## Prerequisites

Before reading this guide, read [agent_tool.md](../agent_tool.md) for the full architecture reference covering the tool class hierarchy, output schemas, registry, and execution lifecycle.

---

## Step-by-Step Process

### Step 1: Create the Tool Class

Create a new file in `genesis-tools/src/genesis_tools/`. Give it a descriptive name matching the tool's purpose.

```python
from pathlib import Path
from typing import Any

from genesis_tools.base import BaseTool
from genesis_tools.schema import ToolResult


class MyToolTool(BaseTool):
    name = "my_tool"
    description = (
        "One-line description of what this tool does. "
        "The LLM reads this to decide when to call the tool."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_param": {
                "type": "string",
                "description": "Description of what this parameter does.",
            },
        },
        "required": ["input_param"],
    }

    async def run(
        self,
        working_directory: Path,
        input_param: str,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            # Tool logic here
            return ToolResult(
                status="success",
                tool_response="What the agent sees after the tool runs.",
            )
        except ValueError as e:
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(
                status="error",
                tool_response=f"Unexpected error: {e!s}",
            )
```

### Step 2: Define Class Attributes

Three class attributes are required:

| Attribute | Purpose |
|---|---|
| `name` | Unique identifier. Used in tool call requests from the LLM. |
| `description` | Human-readable description. Shown to the LLM so it knows when to call the tool. |
| `parameters` | JSON Schema object describing input arguments. |

For any field whose value must come from a fixed set (status, category, type discriminator), you must also declare the allowed values in the JSON schema as an `enum`. The description string is not enough: the model can still produce a value outside the documented list unless the schema contains an explicit `enum` keyword. See [Step 6](#step-6-validate-enum-typed-fields) for the full pattern.

### Step 3: Implement the Run Method

The `run()` method receives framework-injected arguments alongside your tool-specific ones:

| Argument | Type | Description |
|---|---|---|
| `working_directory` | `Path` | Root directory the agent is allowed to operate in. Use this for path validation. |
| `user_db_url` | `str \| None` | Connection to the productivity database. `None` if the subsystem is disabled. |
| `memory_db_url` | `str \| None` | Connection to the memory database. `None` if the subsystem is disabled. |
| `timezone` | `str` | User's configured timezone for rendering dates. |

Key rules:

- **Async only** — wrap blocking I/O with `asyncio.to_thread()`
- **Always validate paths** — call `_validate_path()` before any file operation
- **Return `ToolResult`, never raise** — errors return `status="error"` with a message
- **Catch all exceptions** — unexpected errors return a descriptive error message
- **Validate enum-typed fields at runtime** — schema `enum` is advisory, see [Step 6](#step-6-validate-enum-typed-fields)

### Step 4: Validate Paths

Tools that read or write files must validate paths against the sandbox:

```python
validated_path = self._validate_path(
    working_directory,  # Sandbox root
    path_str,            # Path from the agent
    must_exist=True,     # Raise if path does not exist
    should_be_file=True, # Raise if path is not a file
)
```

This blocks `../etc/passwd` traversal attacks. Validation errors raise `ValueError` which the agent loop catches and converts to an error `ToolResult`.

See [agent_tool.md](../agent_tool.md#tool-base-class) for the full parameter reference.

### Step 5: Choose the Right Output Channel

A `ToolResult` has four independent channels. Use the right one for each kind of output:

| Channel | Use when |
|---|---|
| `tool_response` | Short confirmations, errors, summaries. Goes to chat history. |
| `results_to_add_to_clipboard` | Large text the agent should read without cluttering context. |
| `files_to_add_to_clipboard` | Files the agent should inspect on the next turn. |
| `entities_to_track` | Productivity items (tasks, projects, journals) the agent should monitor. |

### Step 6: Validate Enum-Typed Fields

Any field whose value must come from a fixed set (status, category, type discriminator) must be guarded in two places inside the tool: the JSON schema and the `run()` method.

**Why two layers are not enough.** The two tool-layer guards catch LLM misbehavior and direct API misuse. They do not catch bypass attempts in the service or router layers, which is why the service and router must also validate with Pydantic (the third layer is documented in [agent_tool.md](../agent_tool.md#tool-parameter-schema-design)).

**Pattern:**

```python
from typing import Any

from genesis_core.productivity.models import Status

from genesis_tools.base import BaseTool
from genesis_tools.schema import ToolResult

# Derive the list from the source-of-truth enum so it cannot drift.
_STATUS_VALUES = [s.value for s in Status]


class UpdateTasksTool(BaseTool):
    name = "update_tasks"
    description = "Updates one or more tasks."
    parameters = {
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of task IDs to update.",
            },
            "status": {
                "type": "string",
                "enum": _STATUS_VALUES,
                "description": f"One of {_STATUS_VALUES}.",
            },
        },
        "required": ["task_ids"],
    }

    async def run(
        self,
        working_directory: Path,
        user_db_url: str | None = None,
        task_ids: list[int] = [],
        status: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        # Runtime guard: schema enum is advisory, not enforced.
        if status is not None and status not in _STATUS_VALUES:
            return ToolResult(
                status="error",
                tool_response=f"Invalid status '{status}'. Must be one of {_STATUS_VALUES}.",
            )
        # ... proceed with normal logic
```

The list of allowed values must be derived from the source-of-truth enum (typically a `StrEnum` in `genesis_core.<subsystem>.models`) rather than retyped as a string literal, so the schema and the runtime check stay in lockstep when the enum is extended.

### Step 7: Register the Tool

In `genesis-tools/src/genesis_tools/registry.py`, add an import and a registration call:

```python
from .my_tool import MyToolTool
```

Then add the registration at the bottom of the file:

```python
tool_registry.register("my_tool", MyToolTool)
```

The registry sets `tool_class.name` to match the key, so the class-level `name` attribute is overridden. This ensures the dictionary key and the LLM-visible name are always in sync.

---

## Complete Example: A File-Backed Tool

Here is a tool that reads a file and searches its content:

```python
import asyncio
from pathlib import Path
from typing import Any

from genesis_tools.base import BaseTool
from genesis_tools.schema import ToolResult


class GrepFileTool(BaseTool):
    name = "grep_file"
    description = "Searches for a string within a file."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file, relative to the working directory.",
            },
            "query": {
                "type": "string",
                "description": "String to search for.",
            },
        },
        "required": ["file_path", "query"],
    }

    async def run(
        self,
        working_directory: Path,
        file_path: str,
        query: str,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            validated_path = self._validate_path(
                working_directory,
                file_path,
                must_exist=True,
                should_be_file=True,
            )

            def perform_grep():
                matches = []
                with open(validated_path, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if query in line:
                            matches.append(f"{i}: {line.rstrip()}")
                        if len(matches) >= 100:
                            break
                return matches

            results = await asyncio.to_thread(perform_grep)

            if not results:
                return ToolResult(
                    status="success",
                    tool_response=f"No matches for '{query}' in '{file_path}'.",
                )

            output = f"Found {len(results)} matches:\n" + "\n".join(results)
            return ToolResult(
                status="success",
                tool_response="Search results added to clipboard.",
                results_to_add_to_clipboard=[output],
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(
                status="error",
                tool_response=f"Search failed: {e!s}",
            )
```

Key patterns illustrated:

- Path validation with `should_be_file=True`
- Blocking I/O wrapped in `asyncio.to_thread()`
- Multi-line content returned via `results_to_add_to_clipboard`
- Proper exception handling with `ValueError` for validation and `Exception` for system errors

---

## Tool Location Reference

| Concern | Location |
|---|---|
| Base class and path validation | `genesis-tools/src/genesis_tools/base.py` |
| ToolResult and TrackedEntity schemas | `genesis-tools/src/genesis_tools/schema.py` |
| Registry and all registrations | `genesis-tools/src/genesis_tools/registry.py` |
| File tools | `genesis-tools/src/genesis_tools/file.py` |
| Web tools | `genesis-tools/src/genesis_tools/web_fetch.py`, `web_search.py` |
| Productivity tools | `genesis-tools/src/genesis_tools/productivity_tools.py` |
| Memory tools | `genesis-tools/src/genesis_tools/memory_tools.py` |