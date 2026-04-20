# Adding Entities to the Backend

This guide outlines how to add new database entities and endpoints to the FastAPI backend.

## Quick Overview

The backend implementation spans two Python packages:

- **`genesis-server`** — FastAPI, user management, server databases. Uses `genesis_core` internally.
- **`genesis-core`** — Configuration, agent, workflow engine, registries. No multi-user concept; used directly by the CLI.

## Step 1: Categorize the Entity

Before coding, determine the ownership model to decide where data is stored:

| Ownership | Examples | Storage Location |
|---|---|---|
| **System-wide** | System status snapshots | Main Database |
| **User-owned, System-used** | Custom LLM credentials | Main Database |
| **Private** | Todo lists, journals | User's Private Database |

## Step 2: Create Models and Schemas

### Database Models

Define models in `genesis_server.models` using `sqlmodel`. These define the database table structure. Key patterns:
- Use `Field(index=True)` for frequently queried columns
- Use `UniqueConstraint` for composite uniqueness constraints
- Include `Relationship` for foreign key associations

### Pydantic Schemas

Define schemas in `genesis_server.schemas` to control API input/output. Schemas are often subsets or extensions of models — use `ConfigDict(from_attributes=True)` to allow reading from ORM objects.

## Step 3: Use Dependency Injections

Use `genesis_server.dependencies` to access context at runtime:

| Dependency | Returns | Purpose |
|---|---|---|
| `get_session()` | `Session` | Main database session |
| `get_current_active_user()` | `User` | Authenticated user object |
| `get_user_workdir()` | `Path` | User's isolated sandbox |
| `get_user_config()` | `Config` | User-specific config object |
| `get_agent_registry()` | `AgentRegistry` | AI agent blueprints |
| `get_workflow_registry()` | `WorkflowRegistry` | Workflow manifest registry |
| `get_workflow_engine()` | `WorkflowEngine` | Pre-configured workflow engine |

## Step 4: Write FastAPI Routers

Create a new module in `genesis_server.routers`. Adhere to RESTful principles:

| Path Pattern | Methods | Purpose |
|---|---|---|
| `/resources` | `GET` (list), `POST` (create) | Collection operations |
| `/resources/{id}` | `GET` (detail), `PATCH` (update), `DELETE` | Individual resource operations |

Avoid procedural paths like `/submit-data`; use standard HTTP verbs against resource paths instead.

## Step 5: Integrate

1. Import your router into `genesis_server.main`
2. Include it in the main FastAPI app: `app.include_router(your_router)`
3. Verify the implementation via SwaggerUI at `http://localhost:8000/docs`

## Sandbox Path Validation

When handling file operations, validate paths against the user's sandbox:

1. Resolve the target path relative to the user workdir
2. Check `str(target_dir).startswith(str(user_path.resolve()))` to block traversal
3. Create parent directories with `mkdir(parents=True, exist_ok=True)`
4. Use `os.path.basename()` to strip directory components from filenames

## Key Design Patterns

- **UPSERT logic**: Check for existing record first; update if exists, create if not
- **Soft path traversal protection**: Always validate resolved paths stay within the user's sandbox
- **Session management**: Use `session.commit()` after mutations and `session.refresh()` before returning
