# Productivity System

## Overview

The productivity system provides tasks, projects, journals, and calendar appointments — accessible to agents via tool calls. It is designed so agents can help users manage their work without holding this state in their context.

```
Agent Loop
  search_tasks() → pins task IDs to clipboard → render_to_markdown()
        │
        ▼
Productivity Tools (12 tools)
  search/read/create/update for tasks, projects, journals
        │
        ▼
Productivity Service
  CRUD operations, query builders, bulk updates
        │
        ▼
Productivity Models (per-user SQLite)
  Task, Project, JournalEntry, ProjectTaskLink
```

## Data Model

### Task

The core unit of work. Tasks distinguish between two kinds of time:

**Floating dates** — calendar day only (no time or timezone):
- `assigned_date` — the day the user plans to work on this

**Absolute UTC timestamps** — a specific instant in time:
- `hard_deadline` — a due date with time, e.g. "5pm Friday"
- `scheduled_start` — an appointment start time

The distinction matters: "due Friday" means different things in different timezones. By storing `hard_deadline` as an absolute UTC instant, the system can order deadlines across users in different timezones. Floating `assigned_date` stores just the calendar day.

### Project

A named container for related tasks and journals.

### JournalEntry

A timestamped note. Types: `daily`, `weekly`, `monthly`, `yearly`, `project`, `general`. The `reference_date` is the date the entry is "about" (e.g., the day of a daily journal).

### ProjectTaskLink

Many-to-many join table between Tasks and Projects.

## Time Handling Design

| Kind | Examples | Storage | Meaning |
|---|---|---|---|
| **Floating** | `assigned_date`, project start/deadline | `date` | "The day on the user's calendar" |
| **Absolute** | `hard_deadline`, `scheduled_start` | `datetime(timezone=True)` | "An instant in UTC" |

The frontend converts local times ("9am Friday Adelaide") to UTC before sending to the API. The backend stores UTC. When rendering back, the frontend converts to local time.

## Storage: Per-User Private Database

Productivity data lives in each user's private SQLite database:

```
{internal_state_dir}/productivity/{user_id}.db
```

This is separate from the memory database (`memory/user_memory.db`). The two databases serve different purposes:

- **Productivity DB** — tasks, projects, journals (user's work data)
- **Memory DB** — EventLog, TopicalMemory (agent's learned knowledge about the user)

## Agent Tools

All 12 productivity tools are in `productivity_tools.py`. Each tool pins its results to the clipboard via `TrackedEntity`.

### Search Tools (Pin → Summary)

| Tool | Description |
|---|---|
| `search_tasks` | Filter by status, date range, project, free text. Returns task IDs pinned to clipboard as summaries. |
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

1. **Two clocks**: Floating vs absolute time prevents timezone ambiguity for calendar-day semantics while preserving instant precision for deadlines.
2. **Productivity DB is not the memory DB**: Productivity is user-owned work data; memory is the agent's accumulated knowledge. Different update patterns (CRUD vs append/revise) justify separate storage.
3. **Clipboard as the view layer**: Productivity tools don't return full records in the tool response — they pin IDs and the clipboard rendering handles formatting. Keeps tool responses compact.
4. **Exact-match journal editing**: `edit_journal` requires an exact string match and fails if the string appears multiple times. Journals are long Markdown documents; blindly replacing the first occurrence would be dangerous.
5. **Completion timestamp auto-set**: When a task transitions to `completed`, `completed_at` is auto-set to `now(UTC)`. When transitioning out of `completed`, it is cleared.

## Related Modules

- `genesis_core.productivity` — Productivity database models (`Task`, `Project`, `JournalEntry`, `ProjectTaskLink`)
- `genesis_core.productivity_service` — CRUD operations, query builders, bulk updates
- `genesis_core.tools.productivity_tools` — All 12 productivity agent tools
