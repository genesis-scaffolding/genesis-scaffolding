# Creating New Workflow Steps

This guide walks you through creating a new workflow step (task) from scratch.

For the architecture and design rationale behind workflow tasks, see [workflow_task.md](../workflow_task.md).

---

## What is a Workflow Step?

A workflow step is a reusable Python module that the workflow engine executes as part of a workflow. Each step:
- Receives typed parameters from the workflow manifest
- Performs an operation (fetch data, call an agent, process files, etc.)
- Returns structured output that gets written to the blackboard for downstream steps

---

## The Three-Component Pattern

Every workflow task follows the same pattern with three components:

### 1. Params Model

Defines the input parameters for the task. Extend `TaskParams` to add your own fields.

```python
class MyTaskParams(TaskParams):
    query: str
    max_results: int = 10
    include_metadata: bool = False
```

Fields inherited from `TaskParams` (available to all tasks):
- `files_to_read: list[Path]` — Files to make available to the task
- `sub_directory: str | None` — Subdirectory within the job workspace
- `write_response_to_file: bool` — Whether to write output to file
- `write_response_to_output: bool` — Whether to copy output to job's output directory
- `output_filename: str` — Custom output filename
- `output_filename_prefix: str` — Prefix for multi-item outputs

### 2. Output Model

Defines what the task produces beyond the standard outputs. Extend `TaskOutput` to add custom fields.

```python
class MyTaskOutput(TaskOutput):
    pdf_paths: list[Path] = []
    md_paths: list[Path] = []
```

The base `TaskOutput` provides:
- `content: list[str]` — Text output from the task
- `file_paths: list[Path] | None` — File paths written by the task

### 3. Task Class

Implements the actual logic. Extend `BaseTask[Params, Output]` and implement `run()`.

```python
class MyTask(BaseTask[MyTaskParams, MyTaskOutput]):
    params_model = MyTaskParams
    output_model = MyTaskOutput

    async def run(self, context, agent_registry, params) -> MyTaskOutput:
        args = self.params_model.model_validate(params)
        # ... implementation ...
        return self.output_model(content=[...], file_paths=[...])
```

---

## Step-by-Step Guide

### Step 1: Define the Contract

Before writing code, decide:
- What parameters does the task need? (Define your params model)
- What does the task produce? (Define your output model, or use `TaskOutput` for simple cases)
- Is this a map, reduce, or projection operation? (See [workflow_architecture.md](../workflow_architecture.md))

### Step 2: Create the Task File

Create a new Python file in `genesis_core/workflow_tasks/`. For example, `my_task.py`.

Start with the imports:
```python
import asyncio
from pathlib import Path

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext
from .base_task import BaseTask, TaskOutput, TaskParams
```

### Step 3: Define the Params Model

```python
class MyTaskParams(TaskParams):
    query: str                          # Required: no default
    max_results: int = 10              # Optional: with default
    include_metadata: bool = False      # Optional: boolean with default
```

Type coercion works automatically. Jinja2 templates resolve to strings, but `TaskParams` converts:
- `"true"`/`"false"` → Python `True`/`False`
- `"42"` → `int` 42
- `"3.14"` → `float` 3.14
- `"['a', 'b']"` → `list[str]`

### Step 4: Define the Output Model

If your task only produces text content and file paths, skip this step and use `TaskOutput` directly.

For extra structured output:
```python
class MyTaskOutput(TaskOutput):
    pdf_paths: list[Path] = []
    md_paths: list[Path] = []
```

### Step 5: Implement the Task Class

```python
class MyTask(BaseTask[MyTaskParams, MyTaskOutput]):
    params_model = MyTaskParams
    output_model = MyTaskOutput

    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> MyTaskOutput:
        # Validate parameters first
        args = self.params_model.model_validate(params)

        # Implement your logic here
        # ...

        # Return the output
        return self.output_model(content=[...], file_paths=[...])
```

### Step 6: Register the Task

Open `genesis_core/workflow_tasks/registry.py` and add your task:

```python
from .my_task import MyTask

TASK_LIBRARY = {
    # ... existing entries ...
    "my_task": MyTask,
}
```

Use the key (`"my_task"`) as the `type` in your workflow manifest:
```yaml
steps:
  - id: "my_step"
    type: "my_task"
    params:
      query: "{{ inputs.search_term }}"
      max_results: 5
```

---

## Utilities in BaseTask

These helper methods are available in every task via `self`.

### resolve_input_file_paths

Resolve file/directory paths with deduplication. Handles relative paths against the job context.

```python
files = self.resolve_input_file_paths(
    input_file_paths=args.files_to_read,
    context=context
)
```

Returns a list of absolute `Path` objects. If a path is a directory, it recursively finds all files inside.

### write_content_to_files

Write a list of content strings to files in the job directory.

```python
output_paths = await self.write_content_to_files(
    content=["First item", "Second item"],
    context=context,
    output_filename="results.md",         # Used when content has 1 item
    output_filename_prefix="result_",     # Used when content has multiple items
    write_response_to_output=True,        # Also copy to output/ directory
    extension="md",
    sub_directory="reports"
)
```

Returns a list of `Path` objects for the written files.

### link_or_copy_to_output

Expose internally-written files to the output directory. Tries symlink first, falls back to copy.

```python
output_paths = await self.link_or_copy_to_output(
    context=context,
    internal_file_paths=[Path("/job/internal/report.md")],
    output_filename="final_report.md",
    output_filename_prefix="",
    sub_directory=None
)
```

---

## Working with Async and Threading

The `run()` method is `async`. All blocking I/O must run in a thread to avoid blocking the event loop.

### Wrapping Blocking Operations

Use `asyncio.to_thread()` for any blocking call:

```python
async def run(self, context, agent_registry, params) -> MyTaskOutput:
    args = self.params_model.model_validate(params)

    def blocking_operation():
        # This runs in a thread pool
        result = some_sync_function()
        return result

    result = await asyncio.to_thread(blocking_operation)
    return self.output_model(content=[result])
```

### Example: File Reading

```python
def _read_files():
    contents = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            contents.append(f.read())
    return contents

contents, paths = await asyncio.to_thread(_read_files)
```

### Example: Network Calls

```python
def _fetch_data(url):
    response = requests.get(url)  # Blocking
    return response.json()

data = await asyncio.to_thread(_fetch_data, "https://api.example.com/data")
```

---

## Common Patterns

### Pattern: Fetching Data from an API

Use retry logic and throttling for external APIs.

```python
async def run(self, context, agent_registry, params) -> MyTaskOutput:
    args = self.params_model.model_validate(params)

    results = []
    for i, item in enumerate(args.items):
        # Throttle between requests
        if i > 0:
            await asyncio.sleep(3 + random.uniform(0.5, 1.5))

        # Retry logic
        for attempt in range(3):
            try:
                result = await asyncio.to_thread(self._fetch_item, item)
                results.append(result)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    await asyncio.sleep((attempt + 1) * 10)
                else:
                    print(f"Failed to fetch {item}: {e}")
                    break

    return self.output_model(content=[str(r) for r in results])
```

### Pattern: Processing Input Files

```python
async def run(self, context, agent_registry, params) -> MyTaskOutput:
    args = self.params_model.model_validate(params)

    # Resolve input file paths
    files = self.resolve_input_file_paths(
        input_file_paths=args.files_to_read,
        context=context
    )

    contents = []
    valid_paths = []

    def _process():
        for path in files:
            if path.suffix.lower() in [".md", ".txt"]:
                contents.append(path.read_text(encoding="utf-8"))
                valid_paths.append(path)

    await asyncio.to_thread(_process)

    return self.output_model(content=contents, file_paths=valid_paths)
```

### Pattern: Calling an LLM Agent

```python
async def run(self, context, agent_registry, params) -> MyTaskOutput:
    args = self.params_model.model_validate(params)

    # Create the agent
    agent = agent_registry.create_agent(args.agent, working_directory=context.root)
    if not agent:
        raise Exception(f"Cannot find agent: {args.agent}")

    # Add context files
    files = self.resolve_input_file_paths(args.files_to_read, context)
    for path in files:
        await agent.add_file(path)

    # Call the agent
    response = await agent.step(args.prompt, context.root)

    # Optionally write to file
    if args.write_response_to_file:
        output_paths = await self.write_content_to_files(
            content=[str(response)],
            context=context,
            output_filename=args.output_filename,
            output_filename_prefix=args.output_filename_prefix,
            write_response_to_output=args.write_response_to_output,
        )
        return self.output_model(content=[str(response)], file_paths=output_paths)

    return self.output_model(content=[str(response)])
```

---

## Validation at Runtime

Always call `model_validate()` at the start of `run()`:

```python
async def run(self, context, agent_registry, params) -> MyTaskOutput:
    args = self.params_model.model_validate(params)  # Always validate first
    # Now args.my_field is a proper Python type, not a string
```

This converts Jinja2-resolved strings to their proper types (bool, int, float, list, Path). Without validation, you receive raw strings that may not behave as expected.

---

## Testing Your Task

### Run with a Test Workflow

Create a temporary workflow manifest that uses your task:

```yaml
name: "Test My Task"
steps:
  - id: "test_step"
    type: "my_task"
    params:
      query: "test query"
      max_results: 3
```

### Check the Blackboard

After each step, the workflow engine writes `workflow_state.json` to the job's `internal/` directory. Inspect this to see what your task produced.

### Inspect Job Directories

```
job_root/
├── input/      # User-provided files
├── internal/   # Files written by steps (check here for your task's output)
└── output/     # Final output files
```

---

## Registering Your Task

After creating your task file, register it in `genesis_core/workflow_tasks/registry.py`:

```python
from .my_task import MyTask

TASK_LIBRARY = {
    # ... existing entries ...
    "my_task": MyTask,
}
```

The key in `TASK_LIBRARY` is the type string used in workflow manifests. Choose a name that describes what the task does.

---

## File Structure Summary

```
genesis-core/src/genesis_core/workflow_tasks/
├── base_task.py        # BaseTask, TaskParams, TaskOutput (do not modify)
├── registry.py          # TASK_LIBRARY (add your task here)
├── agent_map.py        # Example: LLM map task
├── agent_reduce.py     # Example: LLM reduce task
├── agent_projection.py # Example: LLM projection task
├── arxiv_download.py   # Example: External API with throttling
├── file_read.py        # Example: File processing
├── my_task.py          # Your new task
└── ...
```

When adding a new task, modify only:
- `my_task.py` (create this file)
- `registry.py` (add to `TASK_LIBRARY`)

Do not modify `base_task.py` unless you are adding infrastructure used by all tasks.