# Documentation Guidelines

This document defines the standards for writing and maintaining documentation in this project.

## Documentation Structure

Root-level docs in `docs/` provide reference for the architecture of the system and key sub-systems.

The docs under `docs/frontend_components/` describe architecture and usage guideline some important and complex reusable frontend component live in `/docs/frontend_components/`. Each doc covers one component or a closely related group of components.

Docs under `docs/developer_guides` provides guidance for differen development tasks like adding new backend entity, frontend pages, or writing new workflows.

## Writing Principles

- Use underscores (`_`) instead of hyphens (`-`) in doc filenames. For example, `creating_agent_manifests.md` not `creating-agent-manifests.md`
- Always read the source code before writing to ensure accuracy
- Keep language simple and paragraphs short to make docs easy to read
- Do not reproduce every line of code. The docs drift from the code over time if they are too detailed. Describe behavior at the level of functions and data flows, not individual lines
- Cross-link to related docs rather than duplicating content. For example, SSE event details should link to the SSE streaming doc, not reproduce it
- Create figures where relevant. Prioritise mermaidjs over ASCII symbols
  - Class diagram for classes and concepts
  - Flow chart for process
  - Sequence diagram for showing concrete function calls and data flows between entities 
- Follow provided templates where possible

## Documentation Update Guide

- Update `backend_architecture.md` if you add or modify routes, modify the dependency injection, or change the server startup and shutdown sequence
- Update `fastapi_reference.md` when adding, removing, or changing endpoint paths, methods, or parameters. Keep it in sync with the actual router files in `genesis-server/src/genesis_server/routers/`
- Update `module_reference.md` after adding, moving, or removing python modules in the backend
- Update `frontend_architecture.md`, `frontend_component_tree.md`, `frontend_data_flow.md`, or `frontend_layout_system.md` if you make changes to the fundamental architecture and data flow of the frontend.
- Update frontend component docs in `docs/frontend_components/` if you update any of the mentioned frontend components
- Add new frontend component docs in `docs/frontend_components/` if you add any important, reusable components. If component is for specific purpose and simple (example, a text edit form that is used for only one page), then you don't need to document
- Update `settings.md` if you modify or add settings
- Update the document index in `docs/architecture.md` if you add or rename or remove any top-level architecture docs
- Update the guide index in `docs/developer_guides_index.md` if you add or rename or remove any of the developer guide

## Frontend Component Documentation Template

Every component doc in `/docs/frontend_components/` must follow this structure. The purpose of each section is to answer specific questions a developer or agent has when working with that component.

### Single-Component Doc

For a component that has no important subcomponents:

```markdown
# ComponentName

## Overview
One or two sentences describing what this component does and when to use it.

## Component Tree
ASCII tree showing the component hierarchy with any important structural details.

## Props
Table of props with types, defaults, and descriptions. Include code examples
showing how a parent component passes both data and callback functions via props.

## Internal State
List of all useState / useRef / useReducer state variables and their purpose.
Explain how the state drives the component's behavior.

## Internal Operations
Explain key technical details — how the component handles async operations,
what external APIs it calls, how it manages side effects, any performance
considerations. This section is for reference when modifying the internals.

## Key Files
List of files with one-line descriptions.
```

### Multi-Component Doc

For a component group (e.g., the chat system), document each subcomponent separately under its own heading:

```markdown
# ComponentGroupName

## Overview
One or two sentences about the system as a whole.

## Subcomponent: SubComponentName

### Overview
One or two sentences about this subcomponent.

### Component Tree
ASCII tree for this subcomponent only.

### Props
Table of props for this subcomponent.

### Internal State
State for this subcomponent.

### Internal Operations
Technical details specific to this subcomponent.

### Key Files
Files related to this subcomponent.

## Subcomponent: AnotherSubComponent

... (same structure)
```

## FastAPI Route Documentation Template

Use this template when adding or updating endpoint documentation in `fastapi_reference.md`. Each route group gets a section with a heading, brief overview, module path, and endpoint table.

```markdown
## GroupName (`/path`)

One or two sentences describing what this group of endpoints does.

**Module:** `genesis-server/src/genesis_server/routers/filename.py`

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/path` | Auth required | One sentence describing what happens |
| POST | `/path/{param}` | Path: `param`, Body: `SchemaName`, Auth required | One sentence describing what happens |
```

### Fields

- **Method** — HTTP method: GET, POST, PATCH, DELETE
- **Path** — Relative path from the group prefix. Use `{param}` for path parameters
- **Params** — Comma-separated list of parameter locations and types: `Path: param_name`, `Query: param_name`, `Body: SchemaName`, `Auth required`. For no-auth endpoints, omit auth from the list
- **Description** — What the endpoint does in one sentence. Include notable behaviors like status codes (e.g., "returns 202 and streams via SSE", "403 if read-only")

### Nesting sub-groups

If a group has distinct sub-groups (e.g., Projects, Tasks, Journals under `/productivity`), use sub-headings:

```markdown
## Productivity (`/productivity`)

CRUD for projects, tasks, and journal entries.

### Projects

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/productivity/projects` | Body: `ProjectCreate`, Auth required | Create project |

### Tasks

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/productivity/tasks` | Query: `project_id`, Auth required | List tasks |
```

