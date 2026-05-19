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

### Step 1: Read the Guide

Before doing anything else, load `docs/developer_guides/create_workflow_step.md` to understand the task implementation patterns and the three-component structure.

### Step 2: Clarify Requirements

Engage with the developer to understand what they want to build. Ask about:

- **Purpose**: What does this task do and why is it needed?
- **Inputs**: What data does this task need to operate?
- **Output**: What does it produce? Just text, or structured data?
- **Dependencies**: Any external services, APIs, or libraries this task must call?

Do not ask about implementation details like params model, output model, or operation type. Those are for the agent to decide.

### Step 3: Create Preliminary Design

Based on the requirements and your understanding of the docs, draft a task design:

- Task name and description
- Input parameters (name, type, required, default)
- Output model (if extending beyond text content)
- Operation type (map, reduce, or projection)
- Key implementation notes

Present this to the developer for review.

### Step 4: Iterate Until Approved

Refine the design based on developer feedback. Repeat until the developer approves.

### Step 5: Implement the Task

Only after approval, implement the task following the patterns in the guide:

1. Create the task file at `genesis-core/src/genesis_core/workflow_tasks/<task_name>.py`
2. Implement the three components (params model, output model, task class)
3. Register the task in `genesis-core/src/genesis_core/workflow_tasks/registry.py`

## Reference

For detailed implementation patterns, examples, and API documentation, read `docs/developer_guides/create_workflow_step.md`. For the architecture behind workflow tasks, read `docs/workflow_task.md`.