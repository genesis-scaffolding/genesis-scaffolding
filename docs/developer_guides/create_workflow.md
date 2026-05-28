# Creating New Workflows

This guide walks you through designing and writing a new workflow manifest from scratch.

## Prerequisites

Before reading this guide:
- Read [workflow_architecture.md](../workflow_architecture.md) to understand the workflow engine, blackboard, and Jinja2 template resolution
- Read [workflow_manifest.md](../workflow_manifest.md) for the schema reference and available field types

---

## Design Mindset

### Think in Data Flow, Not Control Flow

Start by identifying:
- **Initial state**: What data does the workflow start with?
- **Terminal state**: What should the user get at the end?
- **Transformations**: What operations transform the initial state into the terminal state?

Sketch the data flow as a pipeline:

```
inputs → step 1 → step 2 → ... → outputs
```

Do not think in terms of loops, branches, or conditionals. Think in terms of data entering a step and emerging transformed.

### Think in Map-Reduce

Every step operates on arrays. A step either:

| Pattern | What it does | Mental model |
|---------|--------------|---------------|
| **Map** | Apply same operation to each item in a list | `list[A] → list[B]` where same operation applies on every element of A |
| **Reduce** | Take all items and condense them into fewer items | `list[A] → list[B]` where `len(B) < len(A)` |
| **Projection** | Convert a list from one type to another | `list[A] → list[B]` |

A workflow is a composition of these operations. The key is recognizing when each applies:
- Fetching individual URLs (fetch each URL in a list of URLs and return a list of URL content) → Map
- Combining articles into one report (transform a list of articles into one output article) → Reduce
- Extracting relevant URLs from search results (process a list of search results to create a list of relevant URLs) → Projection

---

## Step-by-Step Design Process

### Step 1: Define the Workflow Goal

Write a one-sentence description of what the workflow does. Include who uses it and what they get.

Example: "Search Arxiv for papers on a topic, download them, and produce a summary."

### Step 2: Identify Inputs and Outputs

List the data the workflow needs to receive and the data it must return.

Inputs example:
- `topic`: string (what to search for)
- `max_results`: int (how many papers, default 5)

Outputs example:
- `search_results`: string (summary of found papers)

### Step 3: Sketch the Data Pipeline

Identify each transformation step. For each step, decide:
- What data enters the step?
- What data leaves the step?
- Is it a map, reduce, or projection?

For the Arxiv search workflow:

```
topic (input)
    ↓
web_search (map: query → list of results)
    ↓
agent_projection (projection: search results → list of Arxiv IDs)
    ↓
arxiv_download (map: list of IDs → list of paper content)
    ↓
agent_map (reduce: list of content → single summary)
    ↓
search_results (output)
```

### Step 4: Identify Existing Tasks

Check the [built-in workflow steps](../workflow_architecture.md#built-in-workflow-steps) to see which tasks you can reuse. If a step requires logic not covered by built-in tasks, you may need to create a custom task (see [workflow_task.md](../workflow_task.md)).

For the Arxiv example:
- `web_search` → built-in
- `agent_projection` → built-in
- `arxiv_download` → built-in
- `agent_map` → built-in

No custom tasks needed.

### Step 5: Determine Step Conditions

Decide which steps might be skipped based on prior results. Add `condition` fields to handle empty input cases.

In the Arxiv workflow, steps after `web_search` should only run if results were found:
```yaml
condition: "{{ steps.search_web.content | length > 0 }}"
```

### Step 6: Write the Manifest

With the design in hand, write the YAML manifest following the schema in [workflow_manifest.md](../workflow_manifest.md).

---

## Writing the Manifest

### Define Inputs

Each input needs a type, description, and optional default or required flag.

```yaml
inputs:
  topic:
    type: "string"
    description: "Topic for searching arxiv"
    required: true

  max_results:
    type: "int"
    description: "Max number of papers to retrieve"
    default: 5
```

Available types: `string`, `int`, `float`, `bool`, `file`, `dir`, `list[string]`, `list[file]`.

### Define Steps

Each step has an `id`, `type`, and `params`. The `id` is how you reference the step's output in later steps.

```yaml
steps:
  - id: "search_web"
    type: "web_search"
    params:
      query:
        - "{{ inputs.topic }} arxiv papers latest"
```

The `id` must be unique within the workflow. Use descriptive names like `search_web` or `download_papers`, not `step1`.

### Pass Data Between Steps

Use Jinja2 templates to inject blackboard values into step parameters.

| Reference | What it accesses |
|-----------|------------------|
| `{{ inputs.X }}` | Workflow input named X |
| `{{ steps.Y.content }}` | `content` output from step Y |
| `{{ steps.Y.file_paths }}` | `file_paths` output from step Y |
| `{{ steps.Y.content[0] }}` | First item in the content list |

Example: passing search results to a projection step:
```yaml
  - id: "extract_ids"
    type: "agent_projection"
    params:
      agent: "simple_agent"
      files_to_read: "{{ steps.search_web.file_paths }}"
      prompt:
        - "Extract all Arxiv IDs found in these search results."
      expected_item_type: "Arxiv IDs (e.g., 2301.12345)"
      max_number: "{{ inputs.max_results }}"
```

### Handle Optional Steps with Conditions

Add a `condition` field to skip a step when prior results are empty:
```yaml
  - id: "download_papers"
    type: "arxiv_download"
    condition: "{{ steps.extract_ids.content | length > 0 }}"
    params:
      arxiv_paper_ids: "{{ steps.extract_ids.content }}"
```

### Define Outputs

Map each output to a step's result using Jinja2 templates. Optionally specify a `destination` to copy files to the user's working directory.

```yaml
outputs:
  search_results:
    description: "Summary of search results"
    value: "{{ steps.summarize_results.content[0] }}"
```

For multi-file outputs, use `destination` as a directory:
```yaml
  source_files:
    description: "Downloaded paper files"
    value: "{{ steps.download_papers.file_paths }}"
    destination: "papers/"
```

---

## Example Walkthrough: Arxiv Search Workflow

This section walks through the `arxiv_search_new.yaml` workflow step by step.

### The Workflow

```yaml
name: "Search Arxiv Papers"
description: "Search, download, and summarize relevant papers on Arxiv"
version: "1.0"

inputs:
  topic:
    type: "string"
    description: "Topic for searching arxiv"

  max_results:
    type: "int"
    description: "Max number of papers to retrieve"
    default: 5

steps:
  - id: "search_web"
    type: "web_search"
    params:
      query:
        - "{{ inputs.topic }} arxiv papers latest"

  - id: "extract_ids"
    type: "agent_projection"
    params:
      agent: "simple_agent"
      files_to_read: "{{ steps.search_web.file_paths }}"
      prompt:
        - "Extract all Arxiv IDs found in these search results."
      expected_item_type: "Arxiv IDs (e.g., 2301.12345)"
      max_number: "{{ inputs.max_results }}"

  - id: "download_papers"
    type: "arxiv_download"
    params:
      arxiv_paper_ids: "{{ steps.extract_ids.content }}"

  - id: "summarize_results"
    type: "agent_map"
    params:
      agent: "simple_agent"
      prompts:
        - |
          Please summarize the latest discovered arxiv papers on the topic {{ inputs.topic }}.

          The information about the discovered papers are below as retrieved from Arxiv.

          {{ steps.download_papers.content }}
      write_response_to_file: True
      write_response_to_output: True
      output_filename: "search_result_summary.md"

outputs:
  search_results:
    description: "Summary of search results"
    value: "{{ steps.summarize_results.content[0] }}"
```

### Design Rationale

**Step 1: `search_web` (Map)**
- Input: topic string
- Output: list of search result items
- Task: `web_search` takes a list of queries and returns a list of results. This is a map operation because it transforms one list (queries) into another (results).

**Step 2: `extract_ids` (Projection)**
- Input: search result content
- Output: list of Arxiv IDs
- Task: `agent_projection` parses the search results and extracts only the Arxiv IDs. This is a projection because it converts one list type (raw text) to another (structured IDs) without iterating over items.

**Step 3: `download_papers` (Map)**
- Input: list of Arxiv IDs
- Output: list of paper content
- Task: `arxiv_download` takes a list of paper IDs and fetches each one. This is a map because the same fetch operation applies to each ID.

**Step 4: `summarize_results` (Reduce)**
- Input: list of paper content
- Output: single summary string
- Task: `agent_map` here is used to synthesize all papers into one summary. While the step type is named `agent_map`, the reduction_instruction causes the agent to combine all inputs into a single coherent output. This is a reduce because it condenses many items into one.

### Data Flow in the Blackboard

After step 1, the blackboard contains:
```json
{
  "inputs": { "topic": "machine learning", "max_results": 5 },
  "steps": {
    "search_web": { "content": ["..."], "file_paths": ["/path/to/results.md"] }
  }
}
```

After step 2, the blackboard grows:
```json
{
  "inputs": { "topic": "machine learning", "max_results": 5 },
  "steps": {
    "search_web": { "content": ["..."], "file_paths": [...] },
    "extract_ids": { "content": ["2301.12345", "2401.56789"] }
  }
}
```

After step 3, papers are downloaded and the step holds markdown and PDF paths. Step 4 then synthesizes the content and writes the final summary to `output/search_result_summary.md`.

### Why Not Use Conditions?

This workflow omits conditions on steps 2-4. The reason is that built-in tasks like `arxiv_download` and `agent_projection` handle empty input gracefully. When `extract_ids.content` is empty, `arxiv_download` simply produces no output, and `agent_map` with empty prompts produces no content. The workflow completes without error but produces no meaningful output. In production workflows, you would typically add conditions to prevent downstream steps from running when prior results are empty.
