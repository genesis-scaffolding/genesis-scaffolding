# Configuration System

## Overview

The system uses a layered configuration loading mechanism that resolves settings from multiple sources in priority order, combined with a three-database architecture that separates concerns across system-level, per-user, and memory domains. This design provides flexibility for single- and multi-user deployment, strong isolation guarantees for per-user data, and runtime adaptability for scheduled workloads.

## Config Layers

Configuration is loaded in two successive layers. Each layer performs a deep merge into the accumulated result — the later layer overrides individual fields without replacing entire sub-trees.

### Layer 1: Environment Variables and `.env`

The base layer is populated from the process environment and the `.env` file in the working directory. Pydantic's `BaseSettings` handles both automatically. All environment variables carry the prefix `myproject__`. Nested configuration keys use double underscores (`__`) as separators. For example, `myproject__server__port` maps to `server.port`. This layer ensures the system can be bootstrapped from external infrastructure without any files on disk.

### Layer 2: YAML Override File

On top of the environment layer, the system loads a YAML override file (by default `config.yaml` at the server root, or a path passed to `get_config`). This file represents site-wide defaults shared across all users on the same deployment — the appropriate place for deployment-specific tunings such as server host, port, or feature flags. The `deep_merge` function ensures that adding a new model in YAML does not delete existing models already defined via environment variables.

## Three Databases

The persistent storage layer is split across three purpose-built databases, allowing different retention policies, access patterns, and isolation boundaries to be applied independently.

| Database | Config Key | Scope | Default Location |
|---|---|---|---|
| System DB | `db` | Shared across all users | `server_root_directory/.myproject/database/myproject.db` |
| User DB | `user_db` | Per-User | `internal_state_dir/user_private.db` |
| Memory DB | `memory_db` | Per-User | `internal_state_dir/memory/user_memory.db` |

### System DB

A single shared SQLite database at the server root. It is the system-of-record for all users and contains: user account records, chat session metadata, scheduling entries, and workflow job queues. Its loss affects all users simultaneously.

### User DB

Each user has their own productivity database inside their isolated directory (`user_db`). It holds tasks, projects, and journal entries — the data that is most personal and voluminous. Isolation is enforced by the user-level config override directing its path to a per-user location.

### Memory DB

Each user also has a dedicated memory database alongside the user database (`memory_db`). This stores event logs and topical memory entries that the agent uses to maintain context across interactions. Like the user database, it is fully isolated to its owning user.

## Working Directory Strategy

The working directory is the filesystem location where user-facing operations (file reads, writes, script executions) take place. Its assignment is determined by deployment mode.

**Single-user mode** — the process working directory is used directly. All file operations occur within the same directory tree the server process was started in. No isolation layer.

**Multi-user mode** — each user is assigned a sandboxed working directory at `users/{user_id}/working` relative to a server-provided users directory. This path is set through the user-level config override directing `working_directory` to a per-user location. Each user's agent operates in a completely isolated filesystem view.

## Just-in-Time Context for Scheduling

Scheduled jobs require configuration resolved in the context of the user who owns the job, not the server process at startup. The system resolves user configuration at the moment a scheduled job executes — not when it is queued or when the server starts. If an administrator or user modifies their YAML override file or environment settings, those changes take effect on the next scheduled run without requiring a server restart.

The job queue remains in the shared system database, but the data environments jobs run in are recreated from the current config state at each invocation.

---

## Configuration Reference

All configuration lives under the `Config` model. Environment variables use the prefix `myproject__` with `__` as a nested delimiter (e.g. `myproject__timezone`).

### Top-Level (`Config`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `log_level` | `str` | `"WARNING"` | Log level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL). Case-insensitive; invalid values default to WARNING. Auto-set to DEBUG when running with uvicorn `--reload`. |
| `timezone` | `str` | `"Australia/Adelaide"` | Timezone for datetime operations |
| `providers` | `dict[str, LLMProvider]` | `{}` | LLM provider definitions (see `LLMProvider` below) |
| `models` | `dict[str, LLMModelConfig]` | `{}` | Model definitions keyed by nickname (see `LLMModelConfig` below) |
| `default_model` | `str` | `"default"` | Nickname of the default model to use |
| `path` | `PathConfigs` | auto | Path configuration (see `PathConfigs` below) |
| `server` | `ServerConfig` | auto | Server configuration (see `ServerConfig` below) |
| `db` | `DatabaseConfig` | auto | System-wide database config |
| `user_db` | `DatabaseConfig` | auto | Per-user database config |
| `memory_db` | `DatabaseConfig` | auto | Per-user memory database config |

### `LLMProvider`

| Variable | Type | Default | Description |
|---|---|---|---|
| `name` | `str \| None` | `"openrouter"` | Provider identifier |
| `base_url` | `str \| None` | `"https://openrouter.ai/api/v1"` | API base URL |
| `api_key` | `str` | *(required)* | API key for the provider |

### `LLMModelConfig`

| Variable | Type | Default | Description |
|---|---|---|---|
| `provider` | `str` | *(required)* | Key matching a provider in `providers` |
| `model` | `str` | *(required)* | Model string passed to LiteLLM (e.g. `"anthropic/claude-3-5-sonnet"`) |
| `params` | `dict[str, Any]` | `{}` | Extra params passed to LiteLLM — e.g. `temperature`, `max_tokens`, `reasoning_effort` |

### `ServerConfig`

| Variable | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | `"0.0.0.0"` | Bind address |
| `port` | `int` | `8000` | Bind port |
| `cors_origins` | `list[str]` | `["http://localhost:3000"]` | Allowed CORS origins |
| `cors_origins_extra` | `str` | `""` | Extra CORS origins as a comma-separated string (set via env var `myproject__server__cors_origins_extra`) |
| `jwt_secret_key` | `str` | *(auto-generated)* | Secret for JWT signing; a fresh 32-byte hex value is generated at startup if not provided |
| `algorithm` | `str` | `"HS256"` | JWT algorithm |
| `access_token_expire_minutes` | `int` | `600` | Access token lifetime in minutes |
| `admin_username` | `str \| None` | `None` | Static admin login username |
| `admin_password` | `str \| None` | `None` | Static admin login password |
| `admin_email` | `str \| None` | `None` | Static admin email |

**Computed:** `all_cors_origins` — merges `cors_origins` and `cors_origins_extra` into a single list.

### `DatabaseConfig`

| Variable | Type | Default | Description |
|---|---|---|---|
| `dsn` | `str \| None` | `None` | Full data source name (e.g. `postgresql://...`). If set, overrides `db_directory` and `db_name`. |
| `db_name` | `str` | varies | Database filename (`"myproject.db"`, `"user_private.db"`, or `"memory/user_memory.db"`) |
| `echo_sql` | `bool` | `False` | Whether to log all SQL statements |
| `db_directory` | `Path` | `Path.cwd() / ".myproject" / "database"` | Directory containing the database file |

**Computed:** `connection_string` — returns `dsn` if set, otherwise `sqlite:///«db_directory»/«db_name»`

### `PathConfigs`

| Variable | Type | Default | Description |
|---|---|---|---|
| `working_directory` | `Path` | `Path.cwd()` | Current working context — where file operations occur |
| `server_root_directory` | `Path` | `Path.cwd()` | Where the CLI or server was invoked |

**Computed (read-only properties):**

| Property | Returns |
|---|---|
| `server_users_directory` | `working_directory / "user_directories"` |
| `internal_state_dir` | `working_directory / ".myproject"` |
| `agent_search_paths` | `[PACKAGE_ROOT / "agents", internal_state_dir / "agents"]` |
| `workflow_search_paths` | `[PACKAGE_ROOT / "workflows", internal_state_dir / "workflows"]` |
| `workspace_directory` | `internal_state_dir / "workspaces"` |
| `inbox_directory` | `internal_state_dir / "inbox"` |

---

## Environment Variable Examples

```env
# Top-level
myproject__timezone=UTC
myproject__default_model=claude-3-5-sonnet
myproject__log_level=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Server
myproject__server__host=127.0.0.1
myproject__server__port=9000
myproject__server__cors_origins_extra=https://app.example.com,https://staging.example.com

# Database override (optional — SQLite is default)
myproject__db__dsn=postgresql://user:pass@localhost/myproject
```

## Related Modules

- `myproject_core.configs` — `Config`, `PathConfigs`, `ServerConfig`, `DatabaseConfig`, `get_config()`, `deep_merge()`
- `myproject_core.schemas` — `LLMProvider`, `LLMModelConfig`
