# Routers

## Overview

The FastAPI server uses a modular router structure. Each router handles a distinct domain and is mounted at a prefix. Authentication is enforced per-router via dependency injection.

## Router Map

| Router | Prefix | Responsibility |
|--------|--------|----------------|
| `agents` | `/api/agents` | Agent CRUD, agent registry |
| `auth` | `/auth` | Login, token refresh, logout |
| `chat` | `/api/chats` | Chat sessions, SSE streaming |
| `files` | `/api/files` | File upload/download, sandbox file browser using `LocalSandboxFilesystem` (list, view content, navigate folders) |
| `jobs` | `/api/jobs` | Workflow job status and logs |
| `llm_config` | `/api/llm-config` | LLM provider and model configuration |
| `memory` | `/api/memory` | Agent memory operations |
| `productivity` | `/api/productivity` | Tasks, projects, journals CRUD |
| `schedules` | `/api/schedules` | Cron schedule management |
| `users` | `/api/users` | User account management |
| `workflows` | `/api/workflows` | Workflow manifest management |

### Files Router (`/api/files`)

The files router provides the frontend-facing file operations using `LocalSandboxFilesystem`. File identity is determined by `relative_path` (base64url-encoded for URL safety), not a database ID.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload a file to a subfolder |
| `GET` | `/` | List files in a folder (excludes directories) |
| `GET` | `/folders` | List immediate subdirectories under a parent folder |
| `GET` | `/{file_id}` | Get file metadata by encoded relative path |
| `GET` | `/{file_id}/content` | Get file content as text (for text files) |
| `GET` | `/{file_id}/download` | Download file with proper Content-Disposition |
| `DELETE` | `/{file_id}` | Delete a file |

**File ID Encoding:**

`relative_path` values are base64url-encoded to make them URL-safe:
```python
def _encode_file_id(relative_path: str) -> str:
    return urlsafe_b64encode(relative_path.encode()).rstrip(b"=").decode()
```

**Error Handling:**

- `403 Forbidden` — Path traversal attempt detected
- `404 Not Found` — File or folder does not exist
- `400 Bad Request` — Invalid file ID encoding

**Schemas:**

```python
class SandboxFileRead(BaseModel):
    relative_path: str
    name: str
    is_dir: bool = False
    size: int | None = None
    mime_type: str | None = None
    mtime: float | None = None
    created_at: str | None = None

class FileUploadResponse(BaseModel):
    message: str
    file: SandboxFileRead
```

## Dependency Injection

The `dependencies.py` module provides shared dependency functions used across routers:

| Dependency | Type | Purpose |
|------------|------|---------|
| `get_current_user` | `User` | Decodes JWT, returns the authenticated user |
| `get_current_active_user` | `User` | Checks user is not disabled |
| `get_user_config` | `Config` | Builds per-user config from user-level YAML override |
| `get_user_workdir` | `Path` | Returns the user's sandboxed working directory |
| `get_productivity_session` | `Session` | Opens the user's productivity SQLite database |
| `get_agent_registry` | `AgentRegistry` | User-scoped agent registry |
| `get_workflow_registry` | `WorkflowRegistry` | User-scoped workflow registry |
| `get_workspace_manager` | `WorkspaceManager` | User's workspace manager |
| `get_workflow_engine` | `WorkflowEngine` | Configured workflow engine |
| `get_memory_session` | `Session` | Opens the user's memory SQLite database |
| `get_scheduler_manager` | `SchedulerManager` | System-wide scheduler (from app state) |

The dependency chain ensures user isolation at every layer: `get_current_user` → `get_user_config` → all user-scoped services.

## User Isolation

Each authenticated request is scoped to the calling user through a cascading dependency chain. `get_current_user` decodes the JWT subject claim and retrieves the user record. That user flows into `get_user_workdir`, which resolves the user's sandboxed directory path. From there, `get_user_config` merges the user's YAML override into the base config, giving each service its own isolated view of per-user databases and file paths.

## Related Modules

- `myproject_server.dependencies` — All dependency injection functions
- `myproject_server.routers.agents` — Agent management endpoints
- `myproject_server.routers.auth` — Authentication endpoints
- `myproject_server.routers.chat` — Chat and SSE streaming endpoints
- `myproject_server.routers.files` — File management endpoints
- `myproject_server.routers.jobs` — Workflow job endpoints
- `myproject_server.routers.llm_config` — LLM configuration endpoints
- `myproject_server.routers.memory` — Memory operations endpoints
- `myproject_server.routers.productivity` — Productivity CRUD endpoints
- `myproject_server.routers.schedules` — Schedule management endpoints
- `myproject_server.routers.users` — User account endpoints
- `myproject_server.routers.workflows` — Workflow manifest endpoints
