# Documentation Guidelines

This document defines the standards for writing and maintaining documentation in this project.

## Documentation Structure

### Entry Points (Root-Level Docs)

Root-level docs in `/docs/` provide high-level orientation:

| File | Purpose |
|---|---|
| `architecture.md` | System-level overview of all processes — the primary entry point |
| `module_reference.md` | Detailed module map of all packages and their responsibilities |
| `frontend_architecture.md` | High-level overview of the frontend — framework, communication pattern, tech stack |
| `frontend_data_flow.md` | How browser, Next.js, and FastAPI communicate — server actions, API proxy, token injection |
| `frontend_component_tree.md` | Full component hierarchy from HTML root to page level |
| `frontend_layout_system.md` | CSS constraints, flex rules, PageContainer/PageBody pattern |
| `authentication.md` | JWT structure, login/logout, token refresh, known limitations |
| `backend_architecture.md` | FastAPI backend — DI system, router architecture, startup lifecycle |
| `chat_token_streaming.md` | SSE token streaming from LLM to browser via ActiveRun |
| `scheduled_workflow.md` | APScheduler cron registration and just-in-time workflow execution |
| `llm_client.md` | LiteLLM and Anthropic SDK integration, provider routing |
| `agent_loop.md` | Agent loop architecture, step execution, tool call handling |
| `agent_tool.md` | Tool class hierarchy, execution lifecycle, entity pinning |
| `agent_clipboard.md` | Ephemeral working memory and context injection |
| `agent_manifests.md` | Agent Markdown manifest format with YAML frontmatter |
| `workflow_architecture.md` | Workflow engine, blackboard state, step execution |
| `workflow_manifest.md` | Writing workflow YAML manifests |
| `workflow_task.md` | Building new workflow task types |
| `productivity_subsystem.md` | Productivity data models and service layer |
| `providers.md` | LLM provider and model configuration format |

### Frontend Component Documentation

Frontend component docs live in `/docs/frontend_components/`. Each doc covers one component or a closely related group of components.

See the **Frontend Component Documentation Template** section below for the required structure.

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

- Update `module_reference.md` after adding, moving, or removing python modules in the backend
- Update frontend component docs in `docs/frontend_components/` if you update any of the mentioned frontend components
- Add new frontend component docs in `docs/frontend_components/` if you add any important, reusable components. If component is for specific purpose and simple, you don't need to add docs
- Update `backend_architecture.md` if you add or modify routes, modify the dependency injection, or change the server startup and shutdown sequence
- Update `chat_token_streaming.md` if the SSE event flow, callback chain, or frontend event handlers change
- Update `scheduled_workflow.md` if APScheduler registration, user context resolution, or job execution changes
- Update `llm_client.md` if provider routing, callback signatures, or message conversion changes
- Update `agent_manifests.md` if frontmatter fields, registry loading logic, or the creation/editing flow changes
- Update `providers.md` if provider or model schema fields or API endpoints change

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



## Maintaining Existing Docs

When modifying a component:
- Update the affected section in the component doc
- Check for cross-reference links that may need updating
- If a new prop is added, document it in the Props section with an example
- If internal behavior changes significantly, update the Internal Operations section

Docs are considered part of the codebase change. When committing the code change, include the doc update in the same commit.
