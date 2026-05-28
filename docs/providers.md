# LLM Providers

## Overview

Providers and models are stored as two dictionaries inside the `Config` object: `providers` maps provider nicknames to `LLMProvider` objects, and `models` maps model nicknames to `LLMModelConfig` objects. The `Config` validator ensures every model references a valid provider.

## Schemas

### Provider

```python
class LLMProvider(BaseModel):
    name: str | None = "openrouter"
    base_url: str | None = "https://openrouter.ai/api/v1"
    api_key: str = ...
```

| Field | Description |
|---|---|
| `name` | Provider nickname used internally to reference this provider. Also used by the routing logic — if `name == "minimax"`, the Anthropic SDK is used. |
| `base_url` | The API base URL. Must match what the provider API expects. |
| `api_key` | API key for authentication. Stored securely via environment variable in production. |

### Model

```python
class LLMModelConfig(BaseModel):
    provider: str
    model: str
    params: dict[str, Any] = Field(default_factory=dict)
```

| Field | Description |
|---|---|
| `provider` | Nickname of the provider this model uses. Must match a key in `providers`. |
| `model` | The actual model string passed to the API. This is what the provider API endpoint expects (e.g., `"anthropic/claude-3-5-sonnet"` for LiteLLM, or `"claude-3-5-sonnet-20241022"` for the Anthropic SDK). |
| `params` | Extra arguments forwarded to the API call. Common keys: `max_tokens`, `temperature`, `reasoning_effort`. |

## Config File Format

Providers and models are defined in YAML and merged into the global config. The format:

```yaml
providers:
  openrouter:
    name: openrouter
    base_url: https://openrouter.ai/api/v1
    api_key: sk-or-v1-...

models:
  claude-haiku:
    provider: openrouter
    model: anthropic/claude-3-haiku-20250714
    params:
      max_tokens: 4096
      temperature: 0.7
  gpt-4o-mini:
    provider: openrouter
    model: openai/gpt-4o-mini
    params:
      max_tokens: 4096

default_model: claude-haiku
```

The `default_model` field names the model nickname used when no explicit model is specified (e.g., for new chat sessions).

## Config Layering

The `Config` object is layered. Global defaults are loaded from environment variables and `.env` files. A user-level YAML file at `user_directories/<user_id>/config.yaml` is merged on top using a deep merge that appends to dictionaries rather than replacing them. This means adding a new model entry in the YAML does not delete existing models from the global config.

## API Endpoints

### Get current config

`GET /configs/llm/` — returns the merged `providers`, `models`, and `default_model` for the current user.

```json
{
  "providers": { ... },
  "models": { ... },
  "default_model": "claude-haiku"
}
```

### Add or update a provider

`POST /configs/llm/providers/{nickname}` — body is an `LLMProvider` object. Creates or overwrites the provider entry.

### Delete a provider

`DELETE /configs/llm/providers/{nickname}` — removes the provider. Fails with `400` if models are still using it.

### Add or update a model

`POST /configs/llm/models/{nickname}` — body is an `LLMModelConfig` object. Validates that the referenced provider exists.

```json
{
  "provider": "openrouter",
  "model": "anthropic/claude-3-haiku-20250714",
  "params": { "max_tokens": 4096 }
}
```

### Delete a model

`DELETE /configs/llm/models/{nickname}` — removes the model. Fails with `400` if it is the current default model.

### Update default model

`PATCH /configs/llm/settings` — body is `{"default_model": "claude-haiku"}`. Validates that the model nickname exists.

## Adding a New Provider

1. Define the provider in the config YAML under `providers` with a unique nickname, base URL, and API key.
2. Add one or more model entries under `models` that reference the provider nickname.
3. Set `default_model` to the desired model nickname.

Example — adding Google AI:

```yaml
providers:
  google:
    name: google
    base_url: https://generativelanguage.googleapis.com/v1beta
    api_key: AIza...
  openrouter:
    name: openrouter
    base_url: https://openrouter.ai/api/v1
    api_key: sk-or-v1-...

models:
  gemini-2-0-flash:
    provider: google
    model: gemini-2.0-flash
    params:
      max_tokens: 4096
```

The model string in `model` must match what the provider API accepts. For LiteLLM-compatible providers, the model string may include the provider prefix (e.g., `"openai/gpt-4o"`), but for direct SDK providers it is the bare model name.

## Key Files

| File | Role |
|---|---|
| `genesis-core/src/genesis_core/schemas.py` | `LLMProvider`, `LLMModelConfig` definitions |
| `genesis-core/src/genesis_core/configs.py` | `Config` model with validator, `providers` and `models` dicts |
| `genesis-server/src/genesis_server/routers/llm_config.py` | REST API endpoints for provider and model CRUD |
| `genesis-server/src/genesis_server/utils/config_persistence.py` | YAML read/write helpers for user config files |