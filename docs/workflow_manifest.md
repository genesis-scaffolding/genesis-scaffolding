# Writing Workflow Manifests

This guide walks you through creating a new workflow manifest in `genesis-scaffolding`.

---

## Before you start

1. **Read the workflow architecture docs** — Start with [workflow_architecture.md](workflow_architecture.md) to understand how the workflow engine works, how the blackboard stores state, and how Jinja2 placeholders are resolved.

2. **Review existing workflow tasks** — Check the [Built-in workflow steps](workflow_architecture.md#built-in-workflow-steps) section to see what's already available. You may find a task that does exactly what you need.

3. **Consider building a custom task** — If no existing task fits your use case, see [workflow_task.md](workflow_task.md) for how to create a new workflow task.

---

## Design your workflow

Think in **map-reduce**:

| Pattern | What it does | When to use |
|---------|--------------|-------------|
| **Map** | Same operation on each input item | Processing a list of articles, files, URLs |
| **Reduce** | Synthesize multiple items into one | Summarizing, reporting, combining findings |
| **Projection** | Transform a list into another list | Filtering, extracting, reformatting |

Sketch your data flow:

```
inputs → step 1 → step 2 → ... → outputs
         ↑                ↑
         └──── steps ─────┘
```

Ask yourself:
- What data does the workflow start with?
- What transformations does it apply?
- What should the user get at the end?

---

## Write the manifest

### Required fields

```yaml
name: "My Workflow"
description: "What this workflow does"
steps: []      # At least one step is required
```

### Define inputs

Choose the right type for each input:

| Type | Python | Use for |
|------|--------|---------|
| `string` | `str` | Text, URLs, IDs |
| `int` | `int` | Counts, limits |
| `float` | `float` | Decimal values |
| `bool` | `bool` | Flags |
| `file` | `Path` | Single file path |
| `dir` | `Path` | Single directory path |
| `list[string]` | `list[str]` | Multiple text items |
| `list[file]` | `list[Path]` | Multiple file paths |

Decide whether each input is `required` or has a `default`:

```yaml
inputs:
  query:
    type: "string"
    description: "Search query"
    required: true

  max_results:
    type: "int"
    description: "Maximum number of results"
    default: 10
```

### Write your steps

Steps run **sequentially** in order. Use `id` to name each step — this is how you reference its outputs later.

```yaml
steps:
  - id: "fetch_articles"
    type: "web_search"
    params:
      query: ["{{ inputs.query }}"]
      number_of_results: "{{ inputs.max_results }}"

  - id: "summarize"
    type: "agent_reduce"
    params:
      agent: "my_agent"
      prompts: "{{ steps.fetch_articles.content }}"
```

**Accessing data:**
- `{{ inputs.X }}` — workflow input named X
- `{{ steps.Y.field }}` — output `field` from step Y
- `{{ steps.Y.content[0] }}` — first item in a list

**Skipping steps conditionally:**

```yaml
- id: "optional_step"
  type: "agent_map"
  condition: "{{ inputs.include_analysis }}"   # Skipped if false
  params:
    ...
```

### Define outputs

```yaml
outputs:
  report:
    description: "Final summary report"
    value: "{{ steps.summarize.content }}"
    destination: "reports/summary.md"        # Optional: copy to user's directory
```

---

## Common pitfalls

- **Referencing a step before it runs** — Step outputs can only be accessed after that step has executed.
- **Typos in field names** — Jinja2 won't validate field names. Double-check `{{ steps.my_step.my_field }}`.
- **Confusing `steps` vs `inputs`** — `inputs` are workflow-level. `steps` are intermediate outputs.
- **Wrong data types in templates** — If a param expects a `list[str]` but you pass a single string, coercion may or may not handle it. Be explicit.

---

## Debugging

- **Checkpoints** — The workflow engine saves `workflow_state.json` after each step in the job's `internal/` directory.
- **Job workspace** — Look in `internal/` and `output/` for intermediate files written by tasks.
- **Workflow events** — If you're running via API, callbacks report `step_start`, `step_completed`, and `step_failed` events.
