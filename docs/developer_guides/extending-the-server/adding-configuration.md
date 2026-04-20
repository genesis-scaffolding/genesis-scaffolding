# Adding Configuration Options

This guide explains how to add new configuration options to the system. For a full understanding of the configuration architecture, read [the configuration architecture doc](../../architecture/genesis-core/configuration.md) first.

---

## Overview

The system uses a layered config loading mechanism. When you add a new capability (a new extension, a new tool, a new workflow type), you may need to add new configuration options to support it.

---

## Config Layers (Quick Ref)

| Layer | Source | Overrideable per user? |
|-------|--------|------------------------|
| Environment variables | `genesis__*` env vars | No |
| YAML override file | `config.yaml` at server root | No |
| User-level overrides | User's YAML file | Yes |

Later layers perform a deep merge over earlier layers on a field-by-field basis.

---

## Step 1: Determine the Config Field Location

Ask: does this config option need to be overridable per user, or is it a site-wide setting?

| Use case | Config layer |
|----------|--------------|
| Site-wide defaults (server host, feature flags, model choice) | YAML override in `config.yaml` |
| Per-user isolation (working directory, data paths) | User-level YAML override |
| Secrets or deployment-specific values | Environment variables |

---

## Step 2: Add the Config Field

Config fields are defined in Pydantic settings models in `genesis-core`. The exact module depends on what the config controls:

- `genesis_core.config` — core system config (paths, databases, auth)
- `genesis_core.llm_config` — LLM provider settings
- `genesis_core.agent_config` — agent loop settings

Add a new field to the appropriate model using Pydantic's `Field` with a docstring:

```python
class LLMConfig(BaseSettings):
    model: str = Field(default="claude-sonnet-4-6", description="Default LLM model")
    temperature: float = Field(default=0.0, description="Default sampling temperature")
    # Add new field here:
    custom_setting: str | None = Field(default=None, description="Description of the setting")
```

---

## Step 3: Wire the Config Through

If the new config field affects the server or a specific subsystem, ensure it is passed through dependency injection:

1. **Server-level config** — Add the field to `genesis_core.config.Settings` so it is available via `get_user_config()` dependency.
2. **Tool config** — If a tool needs the config, access it via the tool's `__init__` or `execute` method.
3. **Workflow config** — Workflow manifests can reference config values via `${config:field_name}` syntax.

---

## Step 4: Document the New Option

Add the new config option to the [configuration architecture doc](../../architecture/genesis-core/configuration.md) under the relevant section. Include:

- The full config key path (e.g., `llm.custom_setting`)
- The environment variable name (e.g., `genesis__llm__custom_setting`)
- The default value
- Whether it can be overridden per user

---

## Step 5: Verify

After adding a new config option, verify it loads correctly:

```python
from genesis_core.config import get_config
config = get_config()
print(config.llm.custom_setting)  # should print the value or default
```

---

## Common Patterns

### Adding a feature flag

```python
class AppConfig(BaseSettings):
    new_feature_enabled: bool = Field(default=False, description="Enable the new feature")
```

Set via environment: `genesis__app__new_feature_enabled=true`

### Adding a per-user path override

Per-user paths are naturally overridable via the user-level config layer. Add the field to the path section:

```python
class PathConfig(BaseSettings):
    working_directory: Path = Field(default=Path.cwd(), description="User working directory")
```

---

## Config in Adaptation

When [adapting the scaffolding](../adaptation/decision-process.md) for a new application type, review the configuration guide to determine if your adaptation requires new config options. For example:

- A domain-specific tool may need new API keys or endpoints
- A new LLM provider may need new model or auth settings
- A workflow extension may need new path or timeout settings

Add any new config options before or during the adaptation playbook execution.
