# Settings

`genesis-scaffolding` uses `pydantic-settings` for defining and managing settings used by the Python backend portion of the code base. 

The class `Config` in module `genesis_core.configs` defines all settings used by the system.

Settings are read from `.env` or `config.yaml` files. 

The system uses two tiers of settings. Server-wide settings are configuration specific to the server or defaults shared between users. The user-specific settings are merged over the server's settings to create the specific settings for that that user.


| Location | Scope | 
| --- |--- |
| `<cwd>/.env` | Server-wide settings | 
| `<cwd>/user_directories/<user_id>/config.yaml` | User-specific settings | 


---

## Setting the settings

Place a `.env` file or `config.yaml` file at the expected location to set the settings in the necessary scope.

Environment variables in `.env` file use the prefix `genesis__` with `__` as a nested delimiter. For example

- `genesis__timezone` is the `timezone` setting at the top level
- `genesis__providers__openrouter__name` is equivalent to `configs.providers[openrouter].name`

The repository ships with a `.env.example` as the scaffolding to create new valid `.env` files.

---

## Accessing the settings from code

The `genesis_core.configs` module provides a utility function `get_config(user_workdir: Path | None = None, override_yaml: Path | None = None)` to retrieve the setting instance.

Call this function without parameters to retrieve the server-wide settings.

Supply the `user_workdir` (user's sandbox directory) and `override_yaml` (path to the user's specific `config.yaml`) to retrieve user-specific settings.

Usually, you do not need to call `get_config` function directly. When you write FastAPI code, use the dependency injections in `genesis_server.dependencies` instead.

---

## Backend Settings Reference

All configuration lives under the `Config` model. Environment variables use the prefix `genesis__` with `__` as a nested delimiter (e.g. `genesis__timezone`).

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
| `agent_loop_config` | `AgentLoopConfig` | auto | Agent runtime config (see `AgentLoopConfig` below) |

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
| `cors_origins_extra` | `str` | `""` | Extra CORS origins as a comma-separated string (set via env var `genesis__server__cors_origins_extra`) |
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
| `db_name` | `str` | varies | Database filename (`"genesis.db"`, `"user_private.db"`, or `"memory/user_memory.db"`) |
| `echo_sql` | `bool` | `False` | Whether to log all SQL statements |
| `db_directory` | `Path` | `Path.cwd() / ".genesis" / "database"` | Directory containing the database file |

**Computed:** `connection_string` — returns `dsn` if set, otherwise `sqlite:///«db_directory»/«db_name»`

### `PathConfigs`

| Variable | Type | Default | Description |
|---|---|---|---|
| `working_directory` | `Path` | `Path.cwd()` | Current working context — where file operations occur |
| `server_root_directory` | `Path` | `Path.cwd()` | Where the CLI or server was invoked |

**Computed (read-only properties):**

| Property | Type | Default | Returns |
|---|---|---|---|
| `server_users_directory` | `Path` | auto | `working_directory / "user_directories"` |
| `internal_state_dir` | `Path` | auto | `working_directory / ".genesis"` |
| `agent_search_paths` | `list[Path]` | auto | `[PACKAGE_ROOT / "agent" / "builtin_agents", internal_state_dir / "agents"]` |
| `workflow_search_paths` | `list[Path]` | auto | `[PACKAGE_ROOT / "workflow" / "builtin_workflows", internal_state_dir / "workflows"]` |
| `workspace_directory` | `Path` | auto | `internal_state_dir / "workspaces"` |
| `inbox_directory` | `Path` | auto | `internal_state_dir / "inbox"` |

### `AgentLoopConfig`

| Variable | Type | Default | Description |
|---|---|---|---|
| `clipboard_item_ttl` | `int` | `100` | Time-to-live in number of turns for clipboard items |


---

## Related Modules

- `genesis_core.configs` — `Config`, `PathConfigs`, `ServerConfig`, `DatabaseConfig`, `get_config()`, `deep_merge()`
- `genesis_core.schemas` — `LLMProvider`, `LLMModelConfig`

---

## Frontend Settings

The frontend has only one config variable called `FASTAPI_URL`. It is default to `http://localhost:8000`. 

This configuration works in both bare metal and all-in-one docker image. You unlikely need to modify this setting.
