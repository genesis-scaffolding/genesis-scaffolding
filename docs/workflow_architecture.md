# Workflow Architecture

The Workflow Engine coordinates step-by-step pipelines involving LLM agents. 

This document explains the design idea and some engineering details regarding the implementation of the workflows. See [workflow_manifest.md](workflow_manifest.md) for instructions to write new workflow manifests.

## Table of Contents

TBA

---

## Key Concepts

A **workflow** is a predefined sequence of actions applied on a given set of inputs to create desired outputs. 

A **workflow manifest** is the template for running a workflow. It defines the workflow's inputs, outputs, the sequence of steps connecting inputs and outputs, and any other necessary configurations for these steps. In other words, a workflow manifest defines a *type of workflow*. 

A runtime instance of a workflow is called a **workflow run** or a *job*. For example, if you run the same workflow type three times, you created three separate workflow runs. All of these workflow runs belong to the same workflow type.

In `genesis-scaffolding`, every workflow run maintains a data structure called **the blackboard**. The initial workflow inputs and intermediate outputs of the steps are written on the blackboard. Subsequent steps then can read content from the blackboard as inputs. 

Every workflow run is also assigned a **workspace directory**. This directory stores the blackboard and any files that the workflow run creates. 

The `genesis-scaffolding` uses map-reduce pattern to design workflow and allow you to write workflow manifests directly in YAML. It also provides a **workflow engine** that handles manifest discovery, workflow run creation, and workspace management.

### Map-Reduce workflow design

Each workflow takes a list of inputs and performs a sequence of steps to transform on them to create the final outputs. Each step performs one of three activity types:

**Map**: Applies the same transformation to each element of an input array separately, producing a new array of the same length
**Reduce**: Takes the entire input array and applies one transformation to it as a whole to generate 1 output item
**Projection**: Process the entire input array and generate an array out output (in other words, "projecting" from one array to another array)

For example, a workflow for writing a weekly technology update can consist of the following steps:

1. Retrieve overview and URLs of new articles from tracked websites and blogs (Projection: list of sites -> list of article info)
2. Ask an LLM agent to filter the list of article info and create a list of URLs of relevant articles (Projection: list of article info -> list of URLs)
3. Retrieve the full articles (Map: list of URLs -> list of article content)
4. Ask an LLM agent to write the briefing based on the articles (Reduce: list of article content -> output article)

We chose map-reduce instead of imperative (instructions with branching conditions and loops) because:

- Many workflow steps involve acting on an array of input to create an array of output. With map-reduce, you can model these steps as single actions. If we design workflow with imperative pattern, you will need to write loops and branches over array items to achieve the same results. 
- Map-reduce workflow design allows us to introduce parallel processing in the future without breaking your existing workflows.

### The Blackboard

The blackboard is an object that stores the workflow inputs and intermediate outputs.

The blackboard contains two dictionary objects:

- `inputs`: a dictionary of all workflow inputs
- `steps`: a dictionary of all outputs of workflow steps. Each workflow step has its own entry.

The workflow engine serializes this object to JSON document and store in the workspace directory of the workflow run after every step as a checkpoint mechanism. 

Example blackboard below shows a workflow with three steps. Each step creates between 2 and 4 types of outputs. Each output is a list. Subsequent steps can use a dot notation to access blackboard content. For example, the step `paper_summary` can use `steps.arxiv_download.content[0]` to access the first item in the `content` output of the workflow step `arxiv_download`. 

```json
{
  "inputs": {
    "paper_id": "https://arxiv.org/abs/2603.01896"
  },
  "steps": {
    "arxiv_download": {
      "content": [
        "..."
      ],
      "file_paths": [
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/internal/2603.01896v1.md"
      ],
      "pdf_paths": [
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/internal/2603.01896v1.pdf"
      ],
      "md_paths": [
        "app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/internal/2603.01896v1.md"
      ]
    },
    "paper_summary": {
      "content": [
        "..."
      ],
      "file_paths": [
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/internal/paper_summary.md",
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/output/paper_summary.md"
      ]
    },
    "paper_critic": {
      "content": [
        "..."
      ],
      "file_paths": [
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/internal/paper_review.md",
        "/app/user_directories/1/.genesis/workspaces/20260304_112859_summarize-arxiv-paper/output/paper_review.md"
      ]
    }
  }
}
```

### Workflow manifests

Workflow manifests define the expected inputs of a workflow, its steps, and the data source each step uses as input. 

In other words, a workflow manifest defines the operations a workflow performs and the data flow between those operations. 

`genesis-scaffolding` supports writing workflow manifests as YAML files. 

The example below shows the details of a step within a workflow, with the following information:

- *id*: the step is assigned a unique id `paper_summary`. It means subsequent steps can use `steps.paper_summary.` to access its outputs.
- *type*: the type of workflow steps. See the section below for a list of built-in workflow steps.
- *params*: parameters to pass to the workflow step. Each workflow step has some unique parameters. You can see the `"{{ steps.arxiv_download.file_paths}}"` used to pass the output from the previous step `arxiv_download` to the `files_to_read` parameter of the `paper_summary` step.

```yaml
  - id: "paper_summary"
    type: "agent_map"
    params:
      agent: "research_summary"
      files_to_read: "{{ steps.arxiv_download.file_paths}}"
      prompts: 
        - "The paper to summary is in your clipboard"
      write_response_to_file: True
      write_response_to_output: True
      output_filename: "paper_summary.md"
```

See [workflow_manifest.md](workflow_manifest.md) for detailed instructions on how to write workflow manifest for your workflow.

### Workspace directory

Every workflow execution gets an isolated workspace directory. 

```
job_root/
├── input/      ← user-provided files
├── internal/   ← intermediate artifacts between steps
└── output/     ← final workflow artifacts
```
---

## Implementation details

This section describes some implementation challenges in building the workflow engine and how we address them. 

### Specifying workflows without code 

We tried a workflow-as-code design in an earlier version of `genesis-scaffolding`. However, we found that the abstraction was leaky. For example, to define a new workflow, you need to create a subclass from an abstract base class for workflow, import and create workflow task instances, and then write the python code to string these workflow task instances together, all ensuring that all the type checks pass.  Developer experience was simply not good. 

Therefore, we use YAML files to define workflows instead. You only need to know the required fields of the YAML file, the parameters of available workflow steps, and the map-reduce pattern to define new workflows. The underlying workflow engine can handle all the validation and orchestration logic. 

The manifest contains the following fields:

- `name`: An easy-to-recognize name for identifying the workflow on web UI.
- `description`: Textual description of the workflow
- `version`: Support versioning your workflow
- `inputs`: a dictionary of workflow inputs. Each item has the following fields:
  - `type`: data type of the input field
  - `description`: textual description of this input item
- `steps`: a dictionary of workflow steps. Each item describe a step and has the following fields:
  - `id`: an identifier to reference that step within the workflow
  - `condition`: an optional field containing a Jinja2 expression. If it resolves to false at runtime, this step would be skipped
  - `type`: the type of workflow step. Must match one of the known workflow step types
  - `params`: a dictionary of parameters sent to the workflow step. Each parameter can be a string with Jinja2 placeholders
- `outputs`: a dictionary of workflow outputs. Each item has the following fields:
  - `description`: textual description of the output
  - `value`: a Jinja2 expression that would be resolved to real value at runtime

Example manifest for a paper summarization workflow:

```yaml
name: "Summarize Arxiv Paper"
description: "Download an Arxiv paper and summarize it"
version: "1.0"

inputs:
  paper_id:
    type: "string"
    description: "ID of the Arxiv paper"

steps:
  - id: "arxiv_download"
    type: "arxiv_download"
    params:
      arxiv_paper_ids: 
        - "{{ inputs.paper_id }}"

  - id: "paper_summary"
    type: "agent_map"
    params:
      agent: "research_summary"
      files_to_read: "{{ steps.arxiv_download.file_paths}}"
      prompts: 
        - "The paper to summary is in your clipboard"
      write_response_to_file: True
      write_response_to_output: True
      output_filename: "paper_summary.md"

  - id: "paper_critic"
    type: "agent_map"
    params:
      agent: "research_critic"
      files_to_read: "{{ steps.arxiv_download.file_paths}}"
      prompts: 
        - "The paper to analyze and provide critic is in your clipboard"
      write_response_to_file: True
      write_response_to_output: True
      output_filename: "paper_review.md"


outputs:
  paper_summary:
    description: "Summary of the paper"
    value: "{{ steps.paper_summary.content }}"
  paper_critic:
    description: "Critic of the paper"
    value: "{{ steps.paper_critic.content }}"
  output_path:
    description: "File path to downloaded paper"
    value: "{{ steps.arxiv_download.file_paths }}"
```

### Defining data flows within the manifests with blackboard and Jinja2 templates

When writing workflow manifests, we want to be able to specify decisions such as:

- A step will use the input called `paper_id`
- A step will use the output of a previous step to construct its input parameters in a particular way
- The final output will use a specific output from a prior workflow step

We solve this problem by introducing the blackboard as a way to store intermediate workflow data and allow you to use **Jinja2 template string** to specify precisely how blackboard content would be injected into your parameters or output values.

In particular, you can use strings with `{{ ... }}` such as `"{{ steps.arxiv_download.file_paths }}"` in the manifest. At runtime, the workflow engine would try to substitute these placeholder with content from the blackboard.


### Parameter verifications

A lot of things can go wrong when we external inputs into workflows and workflow steps. For example:

- User forgets to provide a required workflow input at runtime
- User provides invalid workflow inputs, such as incorrect type
- Workflow designer uses nonexistent blackboard value
- The provided output from blackboard is invalid for the required input of the workflow step

We can organise these issues into design issues (invalid workflow manifests) and runtime issues (invalid data value). We address these issues by introducing both *static verification* and *runtime validation*.

#### Static verifications

Static verifications are performed when a workflow manifest is discovered and loaded.

**Manifest schema verification**: Assess the YAML manifest file against schema and reject if any problem is detected

**Detect reference to nonexistent blackboard value**: Conduct a mock run of the workflow against a mock blackboard to detect invalid references. The workflow engine does the following steps:

1. Constructs a **mock blackboard** — for each task, it generates a payload from the task's `output_model` Pydantic schema (using default values and empty strings)
2. Attempts to render every Jinja2 expression in the manifest against this mock blackboard
3. If a template references a field that doesn't exist on the mock (e.g., `{{ steps.nonexistent.content }}`), validation fails immediately

#### Runtime workflow input validation

We use Pydantic to verify workflow inputs at runtime.

**Allowed input data types**

When defining workflow inputs in the manifest, the `type` field accepts one of the following values:


| YAML Type | Python Type | Description |
|-----------|--------------|-------------|
| `string` | `str` | Plain text string |
| `int` | `int` | Integer number |
| `float` | `float` | Floating-point number |
| `bool` | `bool` | Boolean (`true`/`false`) |
| `file` | `Path` | Path to an existing file |
| `dir` | `Path` | Path to an existing directory |
| `list[string]` | `list[str]` | List of strings |
| `list[file]` | `list[Path]` | List of file paths |

**How validation works**

When a workflow run starts, the engine calls `WorkflowManifest.validate_runtime_inputs(raw_data)` to validate all provided inputs:

1. **Required vs optional**: If an input is marked `required: true` and is missing from the input data with no default, validation fails with `"Input '{name}' is required."`
2. **Default values**: If an input is omitted but has a `default` set, the default is used
3. **Type coercion**: Each value is validated using Pydantic's `TypeAdapter` against the target Python type from the `TYPE_MAP`. This handles:
   - String-to-int/float/bool conversion
   - Path conversion for file/dir inputs
   - List element validation for list types
4. **Single-to-list expansion**: If a list-type input receives a single value (string, int, float, or Path), it's automatically wrapped in a list
5. **Existence checks**: For `file` and `dir` types, the validated path is checked with `.is_file()` or `.is_dir()` — a warning is printed if the path doesn't exist or is the wrong type

If validation fails, a `TypeError` is raised describing which input failed and why.

**Input definition schema**

Each input in the manifest's `inputs` dictionary follows this schema:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | One of the allowed data types listed above |
| `description` | string | Yes | Help text displayed to the user |
| `default` | any | No | Default value if input is omitted |
| `required` | bool | No | If `true`, omitting this input is an error (default: `false`) |

**Example**

```yaml
inputs:
  paper_id:
    type: "string"
    description: "URL or ID of the paper to analyze"
    required: true

  max_results:
    type: "int"
    description: "Maximum number of results to return"
    default: 10

  source_files:
    type: "list[file]"
    description: "Files to include in the analysis"
```

In this example, `paper_id` must be provided as a string, `max_results` defaults to `10` if omitted and will be coerced to an integer, and `source_files` accepts a list of file paths.

#### Runtime workflow step parameter validation

Workflow step parameters (defined in the manifest's `params` field) also go through validation. This happens when the workflow engine calls a task's `run()` method.

**The validation flow**

1. The engine resolves Jinja2 placeholders in step params against the blackboard state, producing raw string values
2. The engine passes these raw params as a `dict` to the task's `run()` method
3. **Each task is responsible for validating its own params** by calling `self.params_model.model_validate(params)` at the start of `run()`

**How TaskParams handles Jinja output**

Since Jinja2 always produces strings, `TaskParams` (the base params model) includes two pre-processing validators:

1. **`pre_parse_all_jinja_strings`** — A model-level validator that runs before type checking:
   - Converts `"true"`/`"false"` strings to Python `True`/`False`
   - Converts `"none"` strings to `None`
   - Uses `ast.literal_eval` to auto-parse numbers (`"42"` → `42`), floats (`"3.14"` → `3.14`), lists, and dicts

2. **`validate_to_path_list`** — A field validator for `files_to_read`:
   - Strips `PosixPath(...)` / `WindowsPath(...)` wrappers that Jinja may produce
   - Parses bracket-style string arrays like `"['/path/a', '/path/b']"`
   - Converts all items to `Path` objects

### Running workflows and outputting events

#### Workflow run logic flow

The `WorkflowEngine.run()` method executes a workflow through the following steps:

```
1. Validate runtime inputs
   └─ manifest.validate_runtime_inputs(user_inputs)

2. Create job workspace
   └─ workspace_manager.create_job(manifest.name)

3. Initialize blackboard state
   └─ state = {"inputs": validated_inputs, "steps": {}}

4. Loop through manifest.steps
   │
   ├─ Check condition (skip if false)
   │
   ├─ Resolve Jinja2 placeholders in step params
   │
   ├─ Get task class from TASK_LIBRARY
   │
   ├─ FIRE STEP_START callback
   │
   ├─ Execute: task.run(job_context, agent_registry, resolved_params)
   │   ├─ Success → update blackboard
   │   └─ Exception → FIRE STEP_FAILED callback, re-raise
   │
   ├─ Checkpoint state to workflow_state.json
   │
   └─ FIRE STEP_COMPLETED callback (if successful)

5. Resolve final outputs via Jinja2

6. Publish output files to user's working directory

7. Return WorkflowOutput
```

#### Event callbacks

Callbacks let you subscribe to workflow events. Pass them to `engine.run()`:

```python
async def my_callback(event: WorkflowEvent):
    print(f"[{event.event_type}] {event.message}")

await engine.run(manifest, inputs, step_callbacks=[my_callback])
```

**Event types:**

| Event | When fired | `step_id` | `data` |
|-------|------------|-----------|--------|
| `STEP_START` | Before a task runs | ✅ | — |
| `STEP_COMPLETED` | After a task succeeds | ✅ | Full task output |
| `STEP_FAILED` | When a task throws | ✅ | — |

**Example — listening for step completion:**

```python
async def on_step_done(event: WorkflowEvent):
    if event.event_type == WorkflowEventType.STEP_COMPLETED:
        print(f"Step {event.step_id} produced {len(event.data.get('content', []))} items")

await engine.run(manifest, inputs, step_callbacks=[on_step_done])
```

### Publishing workflow output to user's working directory

After all steps complete, the engine can copy output files from the job directory to the user's working directory. This is declared in the manifest using the `destination` field on each output.

```
manifest.outputs
  └── output_key
        ├── value         — Jinja2 reference to the source data (content string or file paths)
        └── destination   — relative path in the user's working directory (optional)
```

**Single-file outputs**: `destination` is the target filename. The resolved value (a content string or a file path in `output/`) is copied there.

**Multi-file outputs**: `destination` is treated as a directory. All files referenced by the resolved value are copied into it.

```yaml
outputs:
  final_report:
    description: "The completed research report."
    value: "{{ steps.final_synthesis.content[0] }}"
    destination: "research/report.md"           # copy content string to this file

  source_files:
    description: "All source files collected."
    value: "{{ steps.assess_and_extract.file_paths }}"
    destination: "research/raw_sources/"         # copy all files into this directory
```

If `destination` is omitted, no file is copied out of the job directory.

Destination paths support Jinja2 templates referencing `inputs.*` and `steps.*`, just like `value`.

---

## Designing Workflow Tasks to be extensible

Each workflow step uses one type of **workflow tasks**. These tasks are reusable python modules with predefined inputs and outputs. 

The challenge here is designing the workflow tasks in the way that workflow engine can trigger them without knowing about their details. We also need to ensure that it is easy for developers to build new workflow tasks without having to understand the internal details of the workflow engine.

We solve this by defining a abstract base classes in the module `genesis_core.workflow_tasks.base_task`, which are used as base for developers to build new workflow tasks.

See [workflow_task.md](workflow_task.md) for guideline on how to create new workflow tasks.

### Built-in workflow steps

This section documents all built-in workflow tasks available in `genesis-scaffolding`. Each task is registered in `TASK_LIBRARY` and can be referenced in workflow manifests by its type string.

#### Summary Table

| Type | Class | Description |
|------|-------|-------------|
| `agent_map` | `AgentMapTask` | Calls an LLM agent once per input item |
| `agent_reduce` | `AgentReduceTask` | Calls an LLM agent once on the entire input |
| `agent_projection` | `AgentProjectionTask` | Calls an LLM to extract structured data into a list |
| `arxiv_download` | `ArxivDownloadTask` | Downloads papers from arXiv by ID |
| `arxiv_search` | `ArxivSearchTask` | Searches arXiv and downloads matching papers |
| `file_ingest` | `IngestTask` | Ingests files into the job input directory |
| `file_read` | `FileReadTask` | Reads `.md` and `.txt` files |
| `rss_fetch` | `RSSFetchTask` | Fetches entries from RSS feeds |
| `web_fetch` | `WebFetchTask` | Fetches web pages and extracts content |
| `web_search` | `WebSearchTask` | Searches the web and fetches full results |

---

#### Agent Map (`agent_map`)

**Class:** `AgentMapTask`

Applies the same LLM prompt to each element of an input array, producing a new array of the same length.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `str` | *required* | Name of the agent to use |
| `prompts` | `list[str]` | *required* | Prompts to send to the agent (one per input item) |
| `prompts_prefix` | `str` | `None` | Text prepended to each prompt |
| `output_filename` | `str` | `"output.md"` | Filename for the combined response |
| `files_to_read` | `list[Path]` | `[]` | Files to add to the agent's context |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Agent responses (one per prompt) |
| `file_paths` | `list[Path]` | Paths to written files |

---

#### Agent Reduce (`agent_reduce`)

**Class:** `AgentReduceTask`

Calls an LLM agent once on the entire input combined with a separator, producing a single synthesized response.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `str` | *required* | Name of the agent to use |
| `prompts` | `list[str]` | *required* | Information items to synthesize |
| `separator` | `str` | `"\n\n---\n\n"` | How to join the prompts |
| `reduction_instruction` | `str` | `"Please synthesize..."` | Instruction given to the agent |
| `output_filename` | `str` | `"summary_report.md"` | Output filename |
| `files_to_read` | `list[Path]` | `[]` | Supporting files for the agent |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Single synthesized response |
| `file_paths` | `list[Path]` | Paths to written files |

---

#### Agent Projection (`agent_projection`)

**Class:** `AgentProjectionTask`

Calls an LLM to extract structured data from input into a JSON list. Unlike `agent_map`, this does not iterate over input items — it processes the context and returns a parsed list.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `str` | *required* | Name of the agent to use |
| `prompt` | `list[str]` | *required* | Instructions for what to extract |
| `expected_item_type` | `str` | `"strings"` | Description of item type for the LLM |
| `max_number` | `int` | `None` | Limit the number of returned items |
| `output_filename` | `str` | `"extracted_list.json"` | Output filename |
| `files_to_read` | `list[Path]` | `[]` | Files to provide as context |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Extracted items as strings |
| `file_paths` | `list[Path]` | Paths to written files |

---

#### ArXiv Download (`arxiv_download`)

**Class:** `ArxivDownloadTask`

Downloads papers from arXiv by their paper IDs (e.g., `2301.12345`).

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `arxiv_paper_ids` | `list[str]` | *required* | List of arXiv paper IDs to download |
| `write_response_to_output` | `bool` | `True` | Copy PDFs to output directory |
| `output_filename_prefix` | `str` | `"arxiv_"` | Prefix for output filenames |
| `sub_directory` | `str` | `None` | Subdirectory within the job workspace |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Paper details as formatted strings |
| `file_paths` | `list[Path]` | Paths to markdown versions |
| `pdf_paths` | `list[Path]` | Paths to downloaded PDF files |
| `md_paths` | `list[Path]` | Paths to markdown versions |

---

#### ArXiv Search (`arxiv_search`)

**Class:** `ArxivSearchTask`

Searches arXiv for papers matching a query and downloads them.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `str` | *required* | Search query |
| `max_results` | `int` | `5` | Maximum number of papers to retrieve |
| `output_filename_prefix` | `str` | `"arxiv_search_"` | Prefix for output filenames |
| `write_response_to_output` | `bool` | `True` | Copy PDFs to output directory |
| `sub_directory` | `str` | `None` | Subdirectory within the job workspace |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Title and summary for each paper |
| `file_paths` | `list[Path]` | Paths to markdown versions |
| `pdf_paths` | `list[Path]` | Paths to downloaded PDF files |
| `md_paths` | `list[Path]` | Paths to markdown versions |

---

#### File Ingest (`file_ingest`)

**Class:** `IngestTask`

Ingests files into the job's `input/` directory. For PDFs, automatically converts them to Markdown. Preserves raw files for other types.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `files_to_read` | `list[Path]` | *required* | Files to ingest |
| `prune_references` | `bool` | `True` | Remove references section from PDFs |
| `sub_directory` | `str` | `None` | Subdirectory within `input/` |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Summary message (file counts) |
| `file_paths` | `list[Path]` | All ingested files (raw + converted) |
| `readable_paths` | `list[Path]` | Text-readable files (`.md`, `.txt`, converted PDFs) |

---

#### File Read (`file_read`)

**Class:** `FileReadTask`

Reads text-based files (`.md`, `.txt`) and returns their contents.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `files_to_read` | `list[Path]` | *required* | Files to read |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | File contents |
| `file_paths` | `list[Path]` | Paths of successfully read files |

---

#### RSS Fetch (`rss_fetch`)

**Class:** `RSSFetchTask`

Fetches entries from one or more RSS feeds, optionally filtering by recency.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feed_urls` | `list[str]` | *required* | RSS feed URLs |
| `since_days` | `int` | `1` | Only fetch entries from the last N days |
| `output_filename_prefix` | `str` | `"rss_item_"` | Prefix for output files |
| `write_response_to_file` | `bool` | `True` | Write entries to files |
| `sub_directory` | `str` | `None` | Subdirectory within the job workspace |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Formatted feed entries (source, title, link, summary) |
| `file_paths` | `list[Path]` | Paths to written entry files |

---

#### Web Fetch (`web_fetch`)

**Class:** `WebFetchTask`

Fetches web pages by URL and extracts their text content.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `urls` | `list[str]` | *required* | URLs to fetch |
| `output_filename_prefix` | `str` | `"web_page_"` | Prefix for output files |
| `write_response_to_file` | `bool` | `True` | Write content to files |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Page contents with source URL/title header |
| `file_paths` | `list[Path]` | Paths to written files |

---

#### Web Search (`web_search`)

**Class:** `WebSearchTask`

Performs web searches and fetches full content for each result. Supports multiple queries in parallel.

**Params:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `list[str]` | *required* | Search queries (runs in parallel) |
| `number_of_results` | `int` | `10` | Results per query |
| `output_filename_prefix` | `str` | `"search_results"` | Prefix for output files |
| `write_response_to_file` | `bool` | `True` | Write results to files |
| `write_response_to_output` | `bool` | `False` | Copy results to output directory |

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[str]` | Formatted results as Markdown |
| `file_paths` | `list[Path]` | Paths to written result files |


---

## Potential Future Architecture Improvement

**Enforcing model validation in tasks**

Currently, each workflow task is responsible for calling `self.params_model.model_validate(params)` at the start of its `run()` method. If a developer forgets this call, the task will receive raw Jinja-resolved strings without type coercion, leading to subtle bugs.

For example, a task might check `if params["some_bool_param"]:` expecting a Python `bool`, but receive the string `"true"`, which is truthy — yet behaves differently than the actual `True` value.

**Proposed solutions**

1. **Engine-level pre-validation**: The workflow engine validates task params before calling `run()`. This moves validation to a central location and ensures all tasks are validated consistently. Errors would be caught early with clear messages before any task logic executes.

2. **Abstract method signature change**: Refactor `BaseTask.run()` to accept `params: TParams` (the validated model) instead of `params: dict`. This forces subclasses to always validate before using params, as the type system won't allow direct dict access.

3. **Base task wrapper**: Add a `validate()` method to `BaseTask` that's called automatically before `run()`, so subclasses get validation without having to remember to call it themselves.

---

## Related Modules

- `genesis_core.schemas` — Core data models: `WorkflowManifest`, `WorkflowInputType`, `TYPE_MAP`, `InputDefinition`, `StepDefinition`, `OutputDefinition`
- `genesis_core.workflow.workflow_engine` — `WorkflowEngine` and `JobContext`
- `genesis_core.workflow.workflow_publisher` — `OutputPublisher` for copying outputs to working directory
- `genesis_core.workflow.workflow_registry` — `WorkflowRegistry`, manifest discovery and validation
- `genesis_core.workflow.workflow_workspace` — Job directory management
- `genesis_core.workflow_tasks` — Built-in task implementations
- `genesis_core.workflow_tasks.base_task` — `BaseTask`, `TaskParams`, `TaskOutput` (base classes for custom tasks)
- `genesis_core.workflow_tasks.registry` — `TASK_LIBRARY` (task registration)
- `genesis_core.utils` — `resolve_placeholders()`, `evaluate_condition()` (Jinja2 resolution)
