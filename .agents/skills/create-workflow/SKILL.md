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

### Step 1: Clarify Requirements

Before writing any code, engage in a structured Q&A with the developer to fully understand their workflow requirements.

Ask the following questions in order:

1. **Purpose**: What does this workflow accomplish? Who uses it and what do they get?
2. **Inputs**: What data does the workflow need from the user to start?
3. **Outputs**: What should the workflow produce at the end?
4. **Steps**: Describe the high-level steps the workflow should perform. What transformations happen?
5. **Existing Tasks**: Are any steps complex enough to require a custom workflow task? If so, load the `create-workflow-step` skill to create one first before proceeding.
6. **User Context** (optional): Is this workflow for a specific user? If yes, ask for the user ID so the workflow can be placed in their user directory.

For each step, discuss whether it maps to an existing task type (see [Available Task Types](#available-task-types)) or requires a custom task.

### Step 2: Document the Design

After the Q&A, produce a clear summary of:

- Workflow name and description
- Inputs (name, type, required, default)
- Each step (id, type, purpose, map/reduce/projection classification)
- Outputs (name, source)

Present this to the developer for approval before writing any code.

### Step 3: Write the Manifest

Once approved:

1. **Read the guide** — Load `docs/developer_guides/create_workflow.md` to ensure you follow the correct patterns.
2. **Write the YAML manifest** following the patterns in the guide.
3. **Check for custom tasks** — If any step requires a task that does not exist, load the `create-workflow-step` skill and create the task first.
4. **Write the file** to the appropriate location based on user context.

### Step 4: Verify

After writing the manifest:
- Check that all Jinja2 references (`{{ inputs.X }}`, `{{ steps.Y.field }}`) point to valid inputs and steps.
- Ensure step dependencies are in the correct order.
- If user ID was provided, write to `user_directories/<user_id>/.genesis/workflows/`. Otherwise, write to `genesis-core/src/genesis_core/workflow/builtin_workflows/`.

## Output Locations

| Context | Output Directory |
|---------|------------------|
| User-specific workflow | `user_directories/<user_id>/.genesis/workflows/` |
| Built-in workflow | `genesis-core/src/genesis_core/workflow/builtin_workflows/` |

## Available Task Types

Before designing a step, check if an existing task type fits:

| Type | Class | Description |
|------|-------|-------------|
| `agent_map` | `AgentMapTask` | Call an LLM agent once per input item |
| `agent_reduce` | `AgentReduceTask` | Call an LLM agent on the entire input |
| `agent_projection` | `AgentProjectionTask` | Extract structured data into a list |
| `arxiv_download` | `ArxivDownloadTask` | Download papers from ArXiv by ID |
| `arxiv_search` | `ArxivSearchTask` | Search ArXiv and download papers |
| `file_ingest` | `IngestTask` | Ingest files into the job directory |
| `file_read` | `FileReadTask` | Read `.md` and `.txt` files |
| `rss_fetch` | `RSSFetchTask` | Fetch entries from RSS feeds |
| `web_fetch` | `WebFetchTask` | Fetch web pages and extract content |
| `web_search` | `WebSearchTask` | Search the web and fetch results |

If no existing task fits, load the `create-workflow-step` skill to create a custom task.

## Reference

For detailed patterns and examples, read `docs/developer_guides/create_workflow.md`.