---
name: create-workflow
description: >
  Design and create a new workflow manifest in YAML. Use when the user asks to
  "create a workflow", "add a workflow", "write a workflow", or "design a new
  workflow pipeline". This skill handles the full process from understanding
  requirements to producing a working workflow YAML file.
---

# Create Workflow

Design and create a new workflow manifest in YAML.

## Workflow

### Step 1: Read the Guide

Before doing anything else, load `docs/developer_guides/create_workflow.md` to understand the workflow design patterns and manifest structure.

### Step 2: Clarify Requirements

Engage with the developer to understand what they want to build. Ask about:

- **Purpose**: What does this workflow accomplish? Who uses it and what do they get?
- **Inputs**: What data does the user need to provide to start the workflow?
- **Outputs**: What should the user receive at the end?
- **Constraints/Preferences**: Any preferred data sources, output format, or special requirements?
- **User Context**: Is this for a specific user (ask for user ID), or shared across the server?

Do not ask about implementation details like steps, task types, or map/reduce classification. Those are for the agent to decide.

### Step 3: Create Preliminary Design

Based on the requirements and your understanding of the docs, draft a workflow design:

- Workflow name and description
- Inputs (name, type, required, default)
- Steps (id, type, purpose)
- Outputs (name, source)

Present this to the developer for review.

### Step 4: Iterate Until Approved

Refine the design based on developer feedback. Repeat until the developer approves.

### Step 5: Write the Manifest

Only after approval, write the YAML manifest following the patterns in the guide.

- If any step requires a custom task that does not exist, load the `create-workflow-step` skill and create the task first
- If user ID was provided, write to `user_directories/<user_id>/.genesis/workflows/`
- Otherwise, write to `genesis-core/src/genesis_core/workflow/builtin_workflows/`

## Reference

For detailed patterns, examples, and the full list of available task types, read `docs/developer_guides/create_workflow.md`.