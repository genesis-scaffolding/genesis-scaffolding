# Productivity Subsystem

The productivity subsystem provides the data layer for personal task and note management. It is built on a simple philosophical foundation: a productive person needs to record and access two kinds of information — things to do (tasks) and things to remember (notes). Projects bridge the two by representing outcome-level work that spawns actionable tasks.

## Core Entities

### Task

A task is a unit of work the user needs to perform. It lives independently of projects but can be linked to any number of them.

**Time semantics.** Tasks carry three distinct time fields to capture different planning horizons:

| Field | Type | Description |
|-------|------|-------------|
| `hard_deadline` | datetime (UTC) | The firm delivery date. Set by external forces and treated as immutable. |
| `assigned_date` | date | The calendar day the user intends to work on the task. A planning construct, not a fixed appointment. |
| `scheduled_start` | datetime (UTC) | When the task becomes a calendar appointment (meeting, doctor visit). The presence of this field transforms the task into a time-blocked event. |

The separation between `assigned_date` and `hard_deadline` matters. A task may be assigned to Tuesday because that is when the user plans to work on it, while the hard deadline is Friday because the deliverable must be submitted then. Many productivity systems collapse these into one field, which forces the user to maintain a separate planning system outside the application.

**Status lifecycle.** Tasks move through `backlog` -> `todo` -> `in_progress` -> `completed`. The `canceled` status exists for tasks that were abandoned. When a task transitions to `completed`, the system automatically sets `completed_at` to the current UTC time. Reopening a completed task clears `completed_at`.

**Relationships.** Tasks participate in a many-to-many relationship with projects via `ProjectTaskLink`. A task can belong to multiple projects. The `project_ids` property on `Task` provides a convenient accessor for reading linked project IDs.

### Project

A project represents an outcome-level goal that spans multiple sessions to complete. Unlike a task, a project is not something you do in one sitting — it must be broken down into actionable tasks over time.

The need for projects as a first-class entity (rather than a tag or label) arises from long-horizon planning. When drafting a yearly plan, a user may create projects with no tasks yet — they want to capture that the project exists so they can return to it later and flesh out the actions. Without explicit project tracking, this workflow becomes awkward.

**Fields:**

- `name` — required, indexed for search
- `description` — optional markdown content for goals and notes
- `start_date` / `deadline` — floating calendar dates (no time component)
- `status` — same lifecycle as tasks

**Relationships.** Projects own a list of tasks (via the link table) and a list of journal entries (via foreign key on `JournalEntry`).

### Journal Entry

A journal entry is a note. It stores markdown content that the user wants to capture and reference later. Journal entries support long-horizon planning by serving as the containers for daily, weekly, monthly, and yearly planning documents.

**Entry types:**

| Type | Reference Date Behavior |
|------|------------------------|
| `daily` | The specific calendar day |
| `weekly` | Snapped to Monday of the week |
| `monthly` | Snapped to the 1st of the month |
| `yearly` | Snapped to January 1st |
| `project` | Any date, linked to a project via `project_id` |
| `general` | Any date, no normalization |

The normalization behavior for weekly/monthly/yearly journals ensures that only one entry of each type exists per planning period. When the user creates a weekly journal for any date within a week, the system stores Monday of that week as the reference date.

**Fields:**

- `title` — optional, auto-generated if omitted
- `content` — markdown body for goals, reviews, logs
- `entry_type` — indexed for filtering
- `reference_date` — indexed for time-based queries, normalized per type
- `project_id` — optional link for project-specific journals

## Storage Architecture

Each user has a private SQLite database managed by the productivity subsystem. Database access is handled through `genesis_core/productivity/db.py`:

```python
# Get a per-user engine (cached, tables auto-created on first access)
engine = get_user_engine(config=config)

# Context manager for sessions
for session in get_user_session(db_url=user_db_url):
    # work with session
```

The `productivity_metadata` object is a SQLAlchemy `MetaData` instance dedicated to the productivity models. It prevents collisions with metadata used by other parts of the system. Tables are created via `metadata.create_all(engine)` on first access, so no manual migration step is required.

The `get_user_session` function serves as both a FastAPI dependency and a context manager. It yields a `sqlmodel.Session` bound to the user's engine.

## Service Layer

Business logic for productivity entities lives in `genesis_core/productivity/service.py`. The layer provides:

**Projects**

- `get_project(session, project_id)` — fetch by ID
- `list_projects(session, sort_by, order)` — ordered listing
- `create_project(session, data)` — validate and persist
- `update_project(session, project_id, data)` — partial update
- `delete_project(session, project_id)` — remove and cascade links

**Tasks**

- `get_task(session, task_id)` — fetch with projects eagerly loaded
- `list_tasks(session, assigned_on, project_id, include_completed, sort_by, order)` — filtered listing
- `create_task(session, data, project_ids)` — create and optionally link to projects
- `update_task(session, task_id, data)` — partial update with automatic completion timestamp handling
- `delete_task(session, task_id)` — remove
- `bulk_update_tasks(session, task_ids, field_updates, set_project_ids, add_project_ids, remove_project_ids)` — mass update with project link manipulation
- `bulk_delete_tasks(session, task_ids)` — mass removal

**Journals**

- `get_journal(session, journal_id)` — fetch by ID
- `list_journals(session, entry_type, reference_date, sort_by, order)` — filtered listing
- `create_journal(session, data)` — validate and persist
- `update_journal(session, journal_id, data)` — partial update, updates `updated_at` timestamp
- `delete_journal(session, journal_id)` — remove

**Relationships**

- `link_task_to_project(session, task_id, project_id)` — add a link, idempotent
- `unlink_task_from_project(session, task_id, project_id)` — remove a link

The completion timestamp logic is handled automatically inside `update_task` and `bulk_update_tasks`. Setting status to `completed` records the current UTC time; setting status to any other value clears it.

## API Layer

The FastAPI router at `genesis_server/src/genesis_server/routers/productivity.py` exposes the service layer over HTTP. Each entity type has full CRUD routes with additional features:

**Tasks**

- `POST /productivity/tasks` — create with optional `project_ids`
- `GET /productivity/tasks` — paginated listing with `assigned_on` and `project_id` filters
- `GET /productivity/tasks/{task_id}` — single fetch with projects loaded
- `PATCH /productivity/tasks/{task_id}` — partial update
- `DELETE /productivity/tasks/{task_id}` — remove
- `PATCH /productivity/tasks/bulk` — mass field updates and project link changes
- `DELETE /productivity/tasks/bulk` — mass removal

**Projects**

- `POST /productivity/projects`
- `GET /productivity/projects` — sorted listing
- `GET /productivity/projects/{project_id}`
- `PATCH /productivity/projects/{project_id}`
- `DELETE /productivity/projects/{project_id}`

**Journals**

- `POST /productivity/journals`
- `GET /productivity/journals` — with `entry_type`, `reference_date`, `project_id` filters
- `GET /productivity/journals/{journal_id}`
- `PATCH /productivity/journals/{journal_id}`
- `DELETE /productivity/journals/{journal_id}`

**Relationship management**

- `POST /productivity/tasks/{task_id}/projects/{project_id}` — link
- `DELETE /productivity/tasks/{task_id}/projects/{project_id}` — unlink

**Pydantic schemas** in `genesis_server/src/genesis_server/schemas/productivity.py` handle validation. The `UtcDatetime` type alias applies timezone normalization and ISO formatting to all datetime fields: incoming datetimes are converted to UTC, and outgoing datetimes are serialized with the `Z` suffix and millisecond precision.

## Agent Integration

The productivity tools at `genesis_tools/src/genesis_tools/productivity_tools.py` expose the subsystem to the agent loop. Each tool wraps a service function and returns a `ToolResult` that pins the affected entity to the agent clipboard.

**Read tools** (search and retrieve):

- `search_tasks` — filtered search with dynamic OR/AND query logic, default `limit=100` so a full project fits in one call, TTL=10 on results
- `read_task` — full task detail, resolution=detail
- `search_projects` — filtered search by name, description, date range
- `read_project` — full project detail
- `search_journals` — filtered search by type, project, date range, text
- `read_journal` — full markdown content

**Write tools** (create and modify):

- `create_task` — with date parsing and project linking
- `create_project` — with date fields
- `create_journal` — with reference date normalization, duplicate detection for daily/weekly/monthly/yearly types
- `update_tasks` — bulk update with field-level date clearing (pass `""` to clear)
- `update_project` — single update with field clearing
- `edit_journal` — update a journal via one of two content modes: surgical `old_str`/`new_str` replace (exact match, fails on ambiguous matches) or full `new_content` overwrite (for large journals where exact matching is impractical). Also supports renaming via `title` and re-linking via `project_id`

When an entity is pinned to the clipboard, the agent sees a snapshot of its data in the LLM context. The clipboard refreshes pinned entities on every turn via `AgentMemory.sync_entities()`, so the agent always sees current state. The `resolution` field controls how much data is shown — `summary` for list views, `detail` for focused work.

Entity pinning follows this pattern across all tools:

```python
entity = TrackedEntity(item_type="task", item_id=task_id, resolution="detail", ttl=10)
return ToolResult(
    status="success",
    tool_response=f"Task created with ID {task_id}",
    entities_to_track=[entity],
)
```

The TTL of 10 means the entity stays in the clipboard for 10 agent steps before being removed. Resolution decay downgrades `detail` to `summary` when TTL reaches 5, reducing token cost for aging pinned entities.