---
name: create-workflow-step
description: >
  Create a new workflow task (step) as a Python module. Use when the user asks
  to "create a workflow task", "add a task type", "write a new workflow step",
  or "implement a custom workflow task". This skill handles the full process from
  understanding requirements to producing a registered, working task.
---

# Create Workflow Step

Create a new workflow task (step) as a Python module.

## Workflow

### Step 1: Clarify Requirements

Before writing any code, engage in a structured Q&A with the developer to fully understand the task requirements.

Ask the following questions in order:

1. **Purpose**: What does this task do? What is its role in the workflow?
2. **Input Parameters**: What data does this task need? List each parameter with its type and whether it is required or optional.
3. **Output**: What does the task produce? Does it just return text content and file paths, or does it need additional structured output?
4. **Operation Type**: Is this a map, reduce, or projection operation?
   - **Map**: Apply the same operation to each item in an array
   - **Reduce**: Take all items and condense into fewer items
   - **Projection**: Transform a list from one type to another without LLM
5. **Dependencies**: Does this task depend on external services, APIs, or libraries?

### Step 2: Document the Design

After the Q&A, produce a clear summary of:

- Task name and description
- Params model (field name, type, default, required)
- Output model (if extending beyond `content` and `file_paths`)
- Operation type (map/reduce/projection)
- Key implementation notes (API calls, retry logic, file handling, etc.)

Present this to the developer for approval before writing any code.

### Step 3: Implement the Task

Once approved:

1. **Read the guide** — Load `docs/developer_guides/create_workflow_step.md` to ensure you follow the correct patterns.
2. **Create the task file** at `genesis-core/src/genesis_core/workflow_tasks/<task_name>.py`.
3. **Implement the three components**:
   - Params model (extend `TaskParams`)
   - Output model (extend `TaskOutput` or use it directly)
   - Task class (extend `BaseTask[Params, Output]` and implement `run()`)
4. **Register the task** in `genesis-core/src/genesis_core/workflow_tasks/registry.py`.

### Step 4: Verify

After implementation:
- Ensure `params_model.model_validate(params)` is called at the start of `run()`.
- Check that all async operations use `asyncio.to_thread()` for blocking I/O.
- Verify the task is properly registered in `TASK_LIBRARY`.

## File Locations

| File | Purpose |
|------|---------|
| `genesis-core/src/genesis_core/workflow_tasks/base_task.py` | Do not modify. Contains `BaseTask`, `TaskParams`, `TaskOutput` |
| `genesis-core/src/genesis_core/workflow_tasks/<task_name>.py` | Your new task implementation |
| `genesis-core/src/genesis_core/workflow_tasks/registry.py` | Add your task to `TASK_LIBRARY` here |

## Reference

For detailed implementation patterns, examples, and API documentation, read `docs/developer_guides/create_workflow_step.md`. For the architecture behind workflow tasks, read `docs/workflow_task.md`.