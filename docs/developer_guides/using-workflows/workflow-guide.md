# Workflow Guide

This guide covers how to write, invoke, and extend the workflow system.

## Writing a Workflow Manifest

Place a YAML manifest in your workflow search path (e.g., `working_directory/workflows/`). It is automatically discovered and validated.

### Manifest Schema

```yaml
name: "My Workflow"
version: "1.0"

inputs:
  input_key:
    type: "string"          # data type — see Input Types below
    description: "Help text shown in the frontend form"
    default: "value"        # optional default; omit for required inputs
    required: true           # optional; defaults to False

steps:
  - id: "step_id"            # unique identifier for referencing in later steps
    type: "agent_map"        # task type — see Task Types
    params:                  # task-specific parameters
      prompt: "..."

outputs:
  output_key:
    description: "Help text for this output"
    value: "{{ steps.step_id.content }}"   # Jinja2 reference to step output
    destination: "path/to/file"             # optional — copies output to working directory
```

### The Blackboard

During execution, the engine populates a state object. References in the YAML resolve against this structure:

```
inputs.*         — user-provided inputs
steps.{id}.*    — output fields from a previous step
```

Both `params` values and `destination` paths support Jinja2 expressions.

---

## Input Types

Inputs define the fields shown in the frontend form when a user runs the workflow. Each `type` maps to a specific frontend widget.

| YAML Type | Frontend Widget | Notes |
|---|---|---|
| `string` | Text input | Single-line text |
| `int` | Number input | Integer values only |
| `float` | Number input | Floating-point values |
| `bool` | Toggle switch | `true`/`false` |
| `file` | File picker | Single file; path resolved relative to inbox |
| `dir` | Directory picker | Single directory path |
| `list[string]` | Text area | Multiple lines, one string per line |
| `list[file]` | File multi-picker | Multiple files |

Example with mixed input types:

```yaml
inputs:
  research_topic:
    type: "string"
    description: "The topic to research"
    default: ""

  source_papers:
    type: "list[file]"
    description: "PDF papers to analyze"

  max_results:
    type: "int"
    description: "Maximum number of web search results"
    default: 5

  include_raw_sources:
    type: "bool"
    description: "Copy raw source files to working directory"
    default: false
```

---

## Step Data Flow

### Array semantics

Every step input and output is an **array**, even when it contains only one item. This is fundamental to how map and reduce steps work.

```
steps.my_step.content        → always an array, e.g. ["result string"]
steps.my_step.file_paths    → always an array, e.g. ["/path/to/file1", "/path/to/file2"]
```

When referencing a specific element, use array index notation:
```
{{ steps.my_step.content[0] }}   → first element
```

When referencing the whole array:
```
{{ steps.my_step.content }}       → the entire array (used by reduce steps)
```

### How steps compose

The workflow pipeline moves data from inputs → steps → outputs. Here is the full data flow using `simple_single_agent.yaml` as the example:

```yaml
name: "Simple Agent"
version: "1.0"

inputs:
  user_query:
    type: "string"
    description: "The question you want to ask the agent."
    default: "Hello! Tell me a joke."

  input_files:
    type: "list[file]"
    description: "Files to provide to the agent."
    default: []

  output_file_path:
    type: "string"
    description: "Path to store the output file in the working directory"
    default: ""

steps:
  # Ingest user files into the job directory
  - id: "file_ingest_step"
    type: "file_ingest"
    params:
      files_to_read: "{{ inputs.input_files }}"
      # file_ingest_step.readable_paths → array of Path objects

  # Run the agent over the ingested files
  - id: "agent_step"
    type: "agent_map"
    params:
      agent: "simple_agent"
      files_to_read: "{{ steps.file_ingest_step.readable_paths }}"
      prompts:
        - "{{ inputs.user_query }}"
      write_response_to_file: true
      write_response_to_output: true
      output_filename: "agent_response.md"
      # agent_step.content → array of strings (one per prompt, here: 1)
      # agent_step.file_paths → array of Path objects written to output/

outputs:
  # Expose agent text response as a named output
  output_content:
    description: "Text response from the agent"
    value: "{{ steps.agent_step.content }}"
    destination: "{{ inputs.output_file_path }}"   # resolved at runtime from user input

  # Expose the file paths of generated output files
  output_path:
    description: "File paths to output files from the agent"
    value: "{{ steps.agent_step.file_paths }}"
```

**Step-by-step trace:**

1. `inputs.input_files` (array of file paths) is passed to `file_ingest_step`
2. `file_ingest_step` writes symlinks/copies to the job `input/` directory and returns `readable_paths` (array of `Path` objects)
3. `agent_step` receives `files_to_read` (the readable paths array) and `prompts` (one prompt string in this case)
4. The agent runs and produces `content` (array of response strings) and `file_paths` (array of written file paths)
5. `outputs.output_content.value` references `steps.agent_step.content` and `destination` resolves `{{ inputs.output_file_path }}` at runtime
6. `OutputPublisher` copies the resolved output to the user's working directory

### Map vs Reduce

**Map (`agent_map`)** — applies the same transformation to each element of the input array:

```
["input1", "input2", "input3"]
  ↓ agent_map with one prompt
["result1", "result2", "result3"]
```

Each array item is processed independently by the LLM in a single turn. The output array has the same length as the input array.

**Reduce (`agent_reduce`)** — applies one transformation to the entire input array at once:

```
["input1", "input2", "input3"]
  ↓ agent_reduce with one synthesis instruction
["synthesized_result"]
```

The entire array is passed to the LLM in one turn. The output is typically a single synthesized string (e.g., a summary, a report, an outline).

### Designing a pipeline

A typical research pipeline combines both:

```
inputs.research_query
  ↓
define_spec          (reduce)    → 1 research specification string
  ↓
generate_queries     (projection) → N search query strings
  ↓
execute_search       (map)       → N search result objects
  ↓
assess_and_extract  (map)       → M quality-checked source objects  (M ≤ N)
  ↓
create_outline      (reduce)    → 1 outline string
  ↓
final_synthesis     (reduce)    → 1 final report string
```

By combining map and reduce, you can parallelize over items (map) and then synthesize the results (reduce).

---

## Output Publishing

Use the `destination` field on any output to copy files to the user's working directory after the workflow completes.

```yaml
outputs:
  # Single-file output: destination is the target filename
  final_report:
    value: "{{ steps.final_synthesis.content[0] }}"
    destination: "research/report.md"

  # Multi-file output: destination is a directory; all files land inside it
  source_files:
    value: "{{ steps.assess_and_extract.file_paths }}"
    destination: "research/raw_sources/"

  # No destination: output is returned as data only, no file copied
  metadata:
    value: "{{ steps.define_spec.content[0] }}"
```

Destination paths support Jinja2 templates referencing `inputs.*` and `steps.*`, enabling user-directed file paths:

```yaml
destination: "{{ inputs.output_file_path }}"
```

If `destination` is omitted, the output stays in the isolated job directory — the user can still access it via the API but it is not copied to their working directory.

---

## Task Types

### `agent_map`

Applies an LLM prompt to each element of an input array, producing an output array of the same length.

```yaml
- id: "assess_sources"
  type: "agent_map"
  params:
    agent: "simple_agent"
    files_to_read: "{{ steps.search_results.file_paths }}"
    prompts:
      - "Assess the quality of this source..."
```

**Key params:**

| Param | Type | Description |
|---|---|---|
| `agent` | string | Agent name to use |
| `prompts` | list[string] | Prompts executed in order; array length = output length |
| `files_to_read` | list[file] | Files added to agent context |
| `write_response_to_file` | bool | Write responses to job output directory |
| `write_response_to_output` | bool | Include written files in `file_paths` output |
| `output_filename` | string | Filename for single-prompt responses |

**Outputs:** `content` (array of strings), `file_paths` (array of written file paths)

### `agent_reduce`

Passes all input data to the LLM in a single turn to produce a synthesized output.

```yaml
- id: "synthesize"
  type: "agent_reduce"
  params:
    agent: "simple_agent"
    prompts:
      - "Summarize the following sources into a coherent report..."
    output_filename: "final_report.md"
    write_response_to_output: true
```

**Key params:**

| Param | Type | Description |
|---|---|---|
| `agent` | string | Agent name to use |
| `prompts` | list[string] | Prompts joined with separator and sent as one turn |
| `reduction_instruction` | string | Instruction appended after joined prompts |
| `write_response_to_output` | bool | Write response to job output directory |
| `output_filename` | string | Output filename |

**Outputs:** `content` (array of 1 string), `file_paths` (array of written file paths)

### `agent_projection`

Transforms structured data without calling the LLM. Used for reshaping, filtering, or reformatting arrays.

### `file_ingest`

Ingests user-provided files into the job directory. Handles PDFs (converts to Markdown), text files, and symlinks/copies other files.

**Outputs:** `content` (array of text content), `file_paths` (all ingested file paths), `readable_paths` (text-readable file paths)

### `web_search`

Searches the web and returns results.

### `arxiv_search`, `arxiv_download`

Searches and downloads ArXiv papers.

### `web_fetch`

Fetches and parses web pages.

### `rss_fetch`

Fetches and parses RSS/Atom feeds.

---

## Invoking a Workflow Programmatically

```python
from pathlib import Path
from genesis_core.workflow.workflow_engine import WorkflowEngine
from genesis_core.workflow.workflow_registry import WorkflowRegistry
from genesis_core.workflow.workflow_workspace import WorkspaceManager

wm = WorkspaceManager(settings)
reg = WorkflowRegistry(settings)
engine = WorkflowEngine(wm, agent_registry, settings.path.working_directory)

manifest = reg.get_workflow("my_workflow")
user_data = {"input_key": "value"}

result = await engine.run(manifest, user_data, callbacks=[...])
# result.workflow_result  → dict of resolved output values
# result.workspace_directory → job directory path
```

**WorkflowRegistry**: Handles discovery, schema validation, and logic checking.
**WorkflowEngine**: Handles step-by-step execution, template resolution, blackboard updates, and output publishing.

---

## Validation Layers

The workflow engine has three validation layers:

| Layer | When | Purpose |
|---|---|---|
| **Manifest Schema** | On load | YAML structure matches Pydantic schema |
| **Static Logic** | On `engine.run()` | All Jinja2 references resolve against mock blackboard; destinations validated |
| **Runtime Input** | Per-task, before execution | Task's `params_model` validates the coerced input dict |

---

## Developing New Workflow Step Types

Each task type requires three components defined in `genesis_core.workflow_tasks`:

1. **TaskParams**: A Pydantic model defining the task's allowed input parameters
2. **TaskOutput**: A Pydantic model defining the data the task will write back to the blackboard
3. **TaskClass**: A subclass of `BaseTask[TParams, TOutput]` implementing the `run()` logic

See `genesis-core/src/genesis_core/workflow_tasks/base_task.py` for the abstract base class.
