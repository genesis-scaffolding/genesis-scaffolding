# Productivity Tools

## Overview

Productivity tools give the agent CRUD access to the user's tasks, projects, and journals. All productivity tools pin their results to the clipboard via `TrackedEntity`, so the agent can reference them across turns without holding full records in the context window.

## Available Tools

### Search Tools (Pin → Summary)

| Tool | Description |
|---|---|
| `search_tasks` | Filter by status, date range, project, free text. Returns task IDs pinned as summaries. |
| `search_projects` | Filter by status, deadline, name. Returns project IDs pinned as summaries. |
| `search_journals` | Filter by type, date range, text. Returns journal IDs pinned as summaries. |

### Read Tools (Pin → Detail)

| Tool | Description |
|---|---|
| `read_task` | Fetch full task details + project links. Pinned as **detail** resolution. |
| `read_project` | Fetch full project details. Pinned as **detail** resolution. |
| `read_journal` | Fetch full journal markdown content. Pinned as **detail** resolution. |

### Write Tools (Pin → Detail After Create)

| Tool | Description |
|---|---|
| `create_task` | Creates task, pins the new task to clipboard in **detail** mode. |
| `create_project` | Creates project, pins to clipboard in **detail** mode. |
| `create_journal` | Creates journal with type-based reference date normalization. Pins to clipboard in **detail** mode. |
| `update_tasks` | Bulk update tasks. Pinned as **detail** (single) or **summary** (bulk). |
| `update_project` | Update project fields. |
| `edit_journal` | String-replace journal content. Uses exact-match safety: fails if the old string appears more than once. |

## Clipboard Integration

All productivity tools use `TrackedEntity` to pin results to the clipboard. The clipboard renders pinned entities differently per resolution:

| Resolution | Rendered fields |
|---|---|
| **summary** | ID, title/name, status, key dates |
| **detail** | summary + description, project links, full content |

## Key Design Decisions

1. **Clipboard as the view layer**: Productivity tools don't return full records in the tool response — they pin IDs and the clipboard rendering handles formatting. Keeps tool responses compact.
2. **Exact-match journal editing**: `edit_journal` requires an exact string match and fails if the string appears multiple times. Journals are long Markdown documents; blindly replacing the first occurrence would be dangerous.
3. **Completion timestamp auto-set**: When a task transitions to `completed`, `completed_at` is auto-set to `now(UTC)`. When transitioning out of `completed`, it is cleared.

## Related Modules

- `genesis_core.tools.productivity_tools` — All 12 productivity tool implementations
