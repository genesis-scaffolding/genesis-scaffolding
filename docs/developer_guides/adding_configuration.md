# Adding Configuration Options

This guide walks you through adding a new configuration option to the system. For the full architecture reference, see [settings.md](../settings.md).

## Config Layers

| Source | Scope |
|--------|-------|
| `.env` file with `genesis__` prefix | Server-wide defaults |
| `config.yaml` at server root | Server-wide overrides |
| `user_directories/<user_id>/config.yaml` | Per-user overrides |

Later layers perform a deep merge over earlier layers. Per-user settings override server defaults.

---

## Step 1: Add the Field to the Config Model

Config fields live in `genesis-core/src/genesis_core/configs.py` under the `Config` class or a sub-model.

For site-wide settings, add a field directly to `Config`. For related settings, add to the appropriate sub-model (`ServerConfig`, `DatabaseConfig`, `AgentLoopConfig`, etc.).

```python
from pydantic import Field

class AgentLoopConfig(BaseModel):
    clipboard_item_ttl: int = Field(default=100, description="Turns before clipboard items expire")
    # Add new field here
    my_new_setting: str | None = Field(default=None, description="Description of the setting")
```

For a new top-level field:

```python
class Config(BaseSettings):
    # ... existing fields ...
    my_new_setting: str = Field(default="default_value", description="What this setting does")
```

## Step 2: Set via Environment Variable

Environment variables use the prefix `genesis__` with `__` as a nested delimiter:

| Config field | Environment variable |
|---|---|
| `AgentLoopConfig.my_new_setting` | `genesis__agent_loop_config__my_new_setting` |
| `timezone` | `genesis__timezone` |
| `providers.openrouter.name` | `genesis__providers__openrouter__name` |

Add the variable to `.env.example` to document it for deployment.

## Step 3: Set via YAML

In `config.yaml` or a user's `config.yaml`:

```yaml
agent_loop_config:
  my_new_setting: "custom_value"
```

Deep merge means you only need to specify the fields you are changing.

## Step 4: Access the Config

**In FastAPI routes**, use dependency injection:

```python
from genesis_server.dependencies import get_user_config

@router.get("/example")
def example_route(config: Config = Depends(get_user_config)):
    value = config.agent_loop_config.my_new_setting
    return {"setting": value}
```

**In other modules**, call `get_config()`:

```python
from genesis_core.configs import get_config

config = get_config()
value = config.agent_loop_config.my_new_setting
```

See [settings.md](../settings.md) for full details on `get_config()` and user isolation.

## Step 5: Update the Settings Reference

Add the new field to the reference table in [settings.md](../settings.md) under the relevant section. Include the environment variable name, type, default, and description.

## Common Patterns

**Feature flag:**

```python
class AppConfig(BaseModel):
    new_feature_enabled: bool = Field(default=False, description="Enable the new feature")
```

**Path override:**

```python
class PathConfigs(BaseModel):
    working_directory: Path = Field(default_factory=lambda: Path.cwd().resolve())
    my_custom_path: Path | None = Field(default=None, description="Custom path for something")
```

**Provider-specific setting** (add to the relevant `LLMProvider` or `LLMModelConfig` field in `genesis_core/schemas.py`):

```python
class LLMProvider(BaseModel):
    name: str | None = "openrouter"
    api_key: str  # required
    custom_option: str | None = Field(default=None, description="Provider-specific option")
```