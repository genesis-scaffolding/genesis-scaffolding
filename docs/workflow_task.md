# How to build new workflow tasks

Prerequisites: 
- Review the [workflow_architecture.md](workflow_architecture.md) to understand the workflow engine and how it passes parameters to workflow steps.
- Review the module `genesis_core.workflow_tasks.base_task` and familiarise yourself with the abstract base classes used to define a workflow task.

## High-level process

A workflow step is essentially a reusable python module that can be trigged by workflow engine within a workflow run. 

To define a workflow task, you need to determine the following: 

- What is the logic of the task? This would be stored in the `run()` function
- What are the expected input params of the workflow task? You would extend the `TaskParams` class to define your fields
- What would be the extra output from your workflow task? You would extend the `TaskOutput` class to define your extra output fields

---

## Implementation guide

Each workflow task follows a consistent pattern with three components:

**1. Params Model (`*TaskParams`)**

When writing a new workflow task, you define your params by extending `TaskParams`:

```python
class MyCustomTaskParams(TaskParams):
    query: str                          # Inherits files_to_read, sub_directory, etc.
    max_results: int = 10               # Your custom fields with defaults
    include_metadata: bool = False      # Type coercion works automatically
```

The task then validates at runtime:

```python
async def run(self, context, agent_registry, params) -> MyCustomTaskOutput:
    args = self.params_model.model_validate(params)  # Validate first!
    # Now use args.query, args.max_results, etc.
```

Fields inherited from `TaskParams`:
- `files_to_read: list[Path]` — Files to make available to the task
- `sub_directory: str | None` — Subdirectory within the job workspace
- `write_response_to_file: bool` — Whether to write output to file
- `write_response_to_output: bool` — Whether to copy output to job's output directory
- `output_filename: str` — Custom output filename
- `output_filename_prefix: str` — Prefix for multi-item outputs

**2. Output Model (`*TaskOutput`)**

Extends `TaskOutput` to define what the task produces:

```python
class MyCustomTaskOutput(TaskOutput):
    pdf_paths: list[Path]   # Task-specific output field
    md_paths: list[Path]    # Task-specific output field
    # Inherits: content: list[str], file_paths: list[Path] | None
```

**3. Task Class (`*Task`)**

Extends `BaseTask[Params, Output]` and implements the `run()` method:

```python
class MyCustomTask(BaseTask[MyCustomTaskParams, MyCustomTaskOutput]):
    params_model = MyCustomTaskParams
    output_model = MyCustomTaskOutput

    async def run(self, context, agent_registry, params) -> MyCustomTaskOutput:
        args = self.params_model.model_validate(params)  # Always validate!
        # Implement task logic...
        return self.output_model(content=[...], pdf_paths=[...], md_paths=[...])
```

**Key utilities available in BaseTask**

- `self.resolve_input_file_paths(input_file_paths, context)` — Resolve file/dir paths with dedup
- `self.write_content_to_files(...)` — Write content strings to files in internal/output dirs
- `self.link_or_copy_to_output(...)` — Expose internal files to the output directory

---

## Registering your task

To make a custom task available in workflow manifests, you must register it in `TASK_LIBRARY` in `genesis_core/workflow_tasks/registry.py`:

```python
from .my_custom_task import MyCustomTask

TASK_LIBRARY = {
    # ... existing tasks ...
    "my_custom_task": MyCustomTask,
}
```

The key (`"my_custom_task"`) is the type string you'll use in your workflow manifest:

```yaml
steps:
  - id: "my_step"
    type: "my_custom_task"
    params:
      query: "something"
      max_results: 5
```

---

## Examples

See the modules in `genesis_core.workflow_tasks` for example of built-in workflow tasks
