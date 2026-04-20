# Workflow Architecture

## Overview

The Workflow Engine coordinates step-by-step pipelines involving LLM agents. Each workflow is defined by **inputs**, a sequence of **steps**, and **outputs**. Workflows are declared in YAML manifests — no Python code changes needed to add a new pipeline.

## Key Concepts

### The Blackboard

A shared state object accumulated across step execution. Each step writes its output back to the blackboard; subsequent steps read from it via Jinja2 template references.

```
User input: {"writing_topic": "Python uv"}
Step 1 (agent_outline) → writes {content: "...", file_paths: ["..."]}
Step 2 (agent_drafting) → reads {{ steps.agent_outline.content }} → writes {content: "..."}
```

### Job Directory

Every workflow execution gets an isolated workspace:

```
job_root/
├── input/      ← user-provided files
├── internal/   ← intermediate artifacts between steps
└── output/     ← final workflow artifacts
```

This isolates each run and prevents steps from interfering with each other.

### YAML Manifests

Workflows are YAML files with a defined schema. The engine discovers manifests from configured search paths and validates them before execution.

## Map-Reduce Design

The workflow engine follows a **map-reduce pattern** built around **array semantics**. Every step input and output is structured as arrays — even when there is only one item.

### Array Semantics

- Every step output is an **array** of items (e.g., `content: [...]`, `file_paths: [...]`)
- Every step input is also treated as an **array** — the same transformation is applied to each item
- A map step with 5 input items produces 5 output items; a reduce step takes the whole array and produces a new (usually smaller) array

### Task Types

#### Map (`agent_map`)

Applies the same transformation to each element of an input array, producing a new array of the same length.

```
input: [item1, item2, item3]
↓  agent_map (one agent turn per item)
output: ["result1", "result2", "result3"]
```

Example: quality-assessment map step that applies the same evaluation prompt to each search result, producing one verdict per result.

#### Reduce (`agent_reduce`)

Takes the entire input array and applies one transformation to it as a whole, producing a new array (typically of 1 item, but can be any length).

```
input: ["result1", "result2", "result3"]
↓  agent_reduce (one agent turn on the whole array)
output: ["synthesized_summary"]
```

Example: synthesis step that reads all quality-checked sources and writes one coherent report.

#### Projection (`agent_projection`)

Transforms each element of an input array independently, producing a new array. Unlike map, projection does not call the LLM — it performs structured data transformations (e.g., parse, reformat, filter).

#### Built-in Tasks

| Task Type | Description |
|---|---|
| `agent_map` | LLM map over array items in parallel |
| `agent_reduce` | LLM reduce entire array to synthesized output |
| `agent_projection` | Structural transform without LLM |
| `file_ingest` | Ingest files into the job directory |
| `web_search` | Search the web and return results as array |
| `arxiv_search` | Search ArXiv for papers |
| `web_fetch` | Fetch and parse web pages |
| `rss_fetch` | Fetch and parse RSS feeds |

## Output Publishing

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

## Parameter Passing and Static Verification

### Jinja2 Template Resolution

Manifests use Jinja2 to inject blackboard values into task parameters. Before execution, the engine resolves all `{{ ... }}` expressions against the blackboard — including output `destination` fields.

### Static Logic Verification (`_verify_logic`)

The registry performs static verification before any execution begins:

1. It constructs a **mock blackboard** — for each task, it generates a payload from the task's `output_model` Pydantic schema (using default values and empty strings)
2. It attempts to render every Jinja2 expression in the manifest against this mock blackboard
3. If a template references a field that doesn't exist on the mock (e.g., `{{ steps.nonexistent.content }}`), validation fails immediately

This catches broken references at declaration time, not at runtime.

### Runtime Validation

| Layer | When | Purpose |
|---|---|---|
| Manifest schema | On load | YAML structure matches Pydantic schema |
| Static logic | On `engine.run()` call | All Jinja2 references resolve against mock blackboard |
| Runtime input | Per-task, before execution | Task's `params_model` validates the coerced input dict |

## Component Map

| Component | Responsibility |
|---|---|
| **WorkflowEngine** | Executes steps in sequence, resolves templates, updates blackboard, invokes callbacks, publishes outputs |
| **WorkflowRegistry** | Discovers manifests, validates schema, performs static logic verification |
| **WorkflowManifest** | Pydantic schema for YAML structure: inputs, steps, outputs, version |
| **Task base class** | Abstract base (`BaseTask`) parameterized by `TParams` and `TOutput` |
| **OutputPublisher** | Copies output files from job directory to user working directory |
| **Built-in tasks** | agent_map, agent_reduce, agent_projection, file_ingest, web_search, etc. |
| **JobContext** | Carries the job root, input/output/internal paths, and blackboard to each task |

## Related Modules

- `genesis_core.workflow.workflow_engine` — `WorkflowEngine` and `JobContext`
- `genesis_core.workflow.workflow_publisher` — `OutputPublisher` for copying outputs to working directory
- `genesis_core.workflow.workflow_registry` — `WorkflowRegistry`, manifest discovery and validation
- `genesis_core.workflow.workflow_workspace` — Job directory management (`jobs/{job_id}/input|internal|output/`)
- `genesis_core.workflow_tasks` — Built-in task implementations
