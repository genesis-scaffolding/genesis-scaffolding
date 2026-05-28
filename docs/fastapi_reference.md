# FastAPI Reference

This document provides a reference of all available FastAPI endpoints in the genesis-server backend. For details on request/response schemas, see the schema definitions in `genesis-server/src/genesis_server/schemas/`.

## Auth (`/auth`)

Handles login, token refresh, and logout. No authentication required.

**Module:** `genesis-server/src/genesis_server/routers/auth.py`

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/auth/login` | Body: `OAuth2PasswordRequestForm` | Returns access and refresh tokens |
| POST | `/auth/refresh` | Body: `refresh_token` (string) | Issues new access token from refresh token |

## Users (`/users`)

User profile and registration.

**Module:** `genesis-server/src/genesis_server/routers/users.py`

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/users/` | Body: `UserCreate` | Register new user (no auth) |
| GET | `/users/me` | Auth required | Get current user profile |
| PATCH | `/users/me` | Body: `UserUpdate`, Auth required | Update current user profile |

## Chat (`/chats`)

Chat sessions with agent streaming.

**Module:** `genesis-server/src/genesis_server/routers/chat.py`

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/chats/` | Auth required | List all chat sessions (filtered to active agents) |
| POST | `/chats/` | Body: `ChatSessionCreate`, Auth required | Create new chat session |
| GET | `/chats/{session_id}` | Path: `session_id`, Auth required | Get session history with context tokens |
| POST | `/chats/{session_id}/message` | Path: `session_id`, Body: `user_input` (string), Auth required | Send message, returns 202 and streams via SSE |
| GET | `/chats/{session_id}/stream` | Path: `session_id`, Auth required | SSE stream for live token/ reasoning chunks |

## Agents (`/agents`)

Agent blueprint CRUD operations.

**Module:** `genesis-server/src/genesis_server/routers/agents.py`

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/agents/` | Auth required | List all agent blueprints |
| POST | `/agents/` | Body: `AgentCreate`, Auth required | Create new custom agent |
| GET | `/agents/{agent_id}` | Path: `agent_id`, Auth required | Get agent details |
| PATCH | `/agents/{agent_id}` | Path: `agent_id`, Body: `AgentEdit`, Auth required | Update agent definition |
| DELETE | `/agents/{agent_id}` | Path: `agent_id`, Auth required | Delete agent (403 if read-only, 404 if not found) |

## Workflows (`/workflows`)

Workflow manifest listing and detail (read-only registry).

**Module:** `genesis-server/src/genesis_server/routers/workflows.py`

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/workflows/` | Auth required | List all available workflow manifests |
| GET | `/workflows/{workflow_id}` | Path: `workflow_id`, Auth required | Get specific workflow manifest |

## Jobs (`/jobs`)

Workflow job submission, status, output retrieval.

**Module:** `genesis-server/src/genesis_server/routers/jobs.py`

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/jobs/` | Query: `workflow_id`, Body: `inputs` (dict), Auth required | Submit workflow job, returns 202 and runs in background |
| GET | `/jobs/` | Query: `offset`, `limit`, `schedule_id`, Auth required | List jobs for current user |
| GET | `/jobs/{job_id}` | Path: `job_id`, Auth required | Get job details |
| GET | `/jobs/{job_id}/stream` | Path: `job_id`, Auth required | SSE stream for job progress events |
| GET | `/jobs/{job_id}/output` | Path: `job_id`, Auth required | List job output files |
| GET | `/jobs/{job_id}/output/download/{file_path}` | Path: `job_id`, `file_path`, Auth required | Download job output file |

## Schedules (`/schedules`)

Cron schedule CRUD, synced to APScheduler.

**Module:** `genesis-server/src/genesis_server/routers/schedules.py`

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/schedules/` | Body: `WorkflowScheduleCreate`, Auth required | Create new schedule |
| GET | `/schedules/` | Auth required | List all schedules for user |
| GET | `/schedules/{schedule_id}` | Path: `schedule_id`, Auth required | Get schedule details |
| PATCH | `/schedules/{schedule_id}` | Path: `schedule_id`, Body: `WorkflowScheduleUpdate`, Auth required | Update schedule |
| DELETE | `/schedules/{schedule_id}` | Path: `schedule_id`, Auth required | Delete schedule (removes from APScheduler) |

## Productivity (`/productivity`)

Projects, tasks, and journal entries CRUD.

**Module:** `genesis-server/src/genesis_server/routers/productivity.py`

### Projects

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/productivity/projects` | Body: `ProjectCreate`, Auth required | Create project |
| GET | `/productivity/projects` | Query: `sort_by`, `order`, Auth required | List projects |
| GET | `/productivity/projects/{project_id}` | Path: `project_id`, Auth required | Get project |
| PATCH | `/productivity/projects/{project_id}` | Path: `project_id`, Body: `ProjectUpdate`, Auth required | Update project |
| DELETE | `/productivity/projects/{project_id}` | Path: `project_id`, Auth required | Delete project |

### Tasks

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/productivity/tasks` | Body: `TaskCreate`, Auth required | Create task |
| GET | `/productivity/tasks` | Query: `assigned_on`, `project_id`, `include_completed`, `sort_by`, `order`, `offset`, `limit`, Auth required | List tasks (paginated) |
| GET | `/productivity/tasks/{task_id}` | Path: `task_id`, Auth required | Get task |
| PATCH | `/productivity/tasks/{task_id}` | Path: `task_id`, Body: `TaskUpdate`, Auth required | Update task |
| DELETE | `/productivity/tasks/{task_id}` | Path: `task_id`, Auth required | Delete task |
| PATCH | `/productivity/tasks/bulk` | Body: `TaskBulkUpdate`, Auth required | Bulk update tasks |
| DELETE | `/productivity/tasks/bulk` | Body: `task_ids` (list[int]), Auth required | Bulk delete tasks |
| POST | `/productivity/tasks/{task_id}/projects/{project_id}` | Path: `task_id`, `project_id`, Auth required | Link task to project |
| DELETE | `/productivity/tasks/{task_id}/projects/{project_id}` | Path: `task_id`, `project_id`, Auth required | Unlink task from project |

### Journals

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/productivity/journals` | Body: `JournalEntryCreate`, Auth required | Create journal entry |
| GET | `/productivity/journals` | Query: `entry_type`, `reference_date`, `project_id`, `sort_by`, `order`, Auth required | List journal entries |
| GET | `/productivity/journals/{journal_id}` | Path: `journal_id`, Auth required | Get journal entry |
| PATCH | `/productivity/journals/{journal_id}` | Path: `journal_id`, Body: `JournalEntryUpdate`, Auth required | Update journal entry |
| DELETE | `/productivity/journals/{journal_id}` | Path: `journal_id`, Auth required | Delete journal entry |

## Memory (`/memory`)

Event logs and topical memories (persistent memory).

**Module:** `genesis-server/src/genesis_server/routers/memory.py`

### Unified endpoints

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/memory/` | Query: `memory_type`, `tag`, `importance`, `source`, `superseded`, `sort_by`, `order`, `limit`, `offset`, Auth required | List all memories (events + topics) |
| GET | `/memory/search` | Query: `q`, `memory_type`, `limit`, Auth required | Full-text search using FTS5 |
| GET | `/memory/tags` | Auth required | Get tag counts across all memories |

### Events

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/memory/events` | Query: `tag`, `importance`, `source`, `sort_by`, `order`, `limit`, `offset`, Auth required | List event logs |
| GET | `/memory/events/{event_id}` | Path: `event_id`, Auth required | Get event log |
| POST | `/memory/events` | Body: `EventLogCreate`, Auth required | Create event log |
| PATCH | `/memory/events/{event_id}` | Path: `event_id`, Body: `EventLogUpdate`, Auth required | Update event log |
| DELETE | `/memory/events/{event_id}` | Path: `event_id`, Auth required | Delete event log |

### Topics

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/memory/topics` | Query: `superseded`, `tag`, `importance`, `source`, `sort_by`, `order`, `limit`, `offset`, Auth required | List topical memories |
| GET | `/memory/topics/{topic_id}` | Path: `topic_id`, Auth required | Get topical memory |
| GET | `/memory/topics/{topic_id}/chain` | Path: `topic_id`, Auth required | Get revision chain for topic |
| POST | `/memory/topics` | Body: `TopicalMemoryCreate`, Auth required | Create topical memory |
| PATCH | `/memory/topics/{topic_id}` | Path: `topic_id`, Body: `TopicalMemoryUpdate`, Auth required | Update topical memory |
| POST | `/memory/topics/{topic_id}/supersede` | Path: `topic_id`, Body: `content` (string), Query: `subject`, `tags`, Auth required | Create new revision, supersede old |
| DELETE | `/memory/topics/{topic_id}` | Path: `topic_id`, Auth required | Delete topical memory |

## LLM Config (`/configs/llm`)

LLM provider and model configuration.

**Module:** `genesis-server/src/genesis_server/routers/llm_config.py`

| Method | Path | Params | Description |
|---|---|---|---|
| GET | `/configs/llm/` | Auth required | Get all providers, models, and default model |
| POST | `/configs/llm/providers/{nickname}` | Path: `nickname`, Body: `LLMProvider`, Auth required | Create or update provider |
| DELETE | `/configs/llm/providers/{nickname}` | Path: `nickname`, Auth required | Delete provider (fails if models depend on it) |
| POST | `/configs/llm/models/{nickname}` | Path: `nickname`, Body: `LLMModelConfig`, Auth required | Create or update model |
| DELETE | `/configs/llm/models/{nickname}` | Path: `nickname`, Auth required | Delete model (fails if it is default) |
| PATCH | `/configs/llm/settings` | Body: `UpdateDefaultModelRequest`, Auth required | Update default model |

## Files (`/files`)

File upload, browse, and delete via sandbox filesystem.

**Module:** `genesis-server/src/genesis_server/routers/files.py`

| Method | Path | Params | Description |
|---|---|---|---|
| POST | `/files/upload` | Body: multipart file, Query: `subfolder`, Auth required | Upload file |
| GET | `/files/` | Query: `folder`, Auth required | List files in folder |
| GET | `/files/folders` | Query: `parent_folder`, Auth required | List subdirectories |
| POST | `/files/folders` | Body: `CreateFolderRequest`, Auth required | Create directory |
| GET | `/files/{file_id}` | Path: `file_id` (base64 encoded path), Auth required | Get file info |
| GET | `/files/{file_id}/content` | Path: `file_id`, Auth required | Get file content as text (UTF-8) |
| GET | `/files/{file_id}/download` | Path: `file_id`, Auth required | Download file |
| DELETE | `/files/{file_id}` | Path: `file_id`, Auth required | Delete file |
| POST | `/files/move` | Body: `FileMoveRequest`, Auth required | Move files to destination folder |
