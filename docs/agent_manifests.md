# Agent Manifests

## Overview

Agents are defined by Markdown files with YAML frontmatter. The frontmatter holds all metadata fields (name, model, tools, system prompt settings), and the markdown body is the system prompt text. The `AgentRegistry` scans directories for `.md` files, parses them with `python-frontmatter`, resolves the LLM model reference from the user's config, and stores each result as an `AgentConfig` blueprint.

## Manifest Format

```yaml
---
name: "Max"
description: "Max is a helpful and professional assistant"
model_name: "claude-haiku"
interactive: true
read_only: true
allowed_tools:
  - search_web
  - read_file
  - write_file
  - search_tasks
allowed_agents: []
is_default: true
---

You are Max, a helpful AI assistant.

You keep your language clear and concise. You do not use em-dash.
```

The `---` delimiters mark the YAML frontmatter section. Everything after the closing `---` is the system prompt body.

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | — | Human-readable name. Shown in the UI and used for display. |
| `description` | `str` | — | Short description. Shown in the UI agent picker. |
| `model_name` | `str` | `""` | Nickname of the model to use, as defined in the user's config under `models`. If omitted, the agent uses the user's default model. |
| `interactive` | `bool` | `false` | If `true`, the agent can be selected for chat sessions. Non-interactive agents are only usable internally by workflows. |
| `read_only` | `bool` | `false` | If `true`, the agent cannot be edited or deleted through the API. Built-in agents shipped with the package are marked `read_only: true`. |
| `allowed_tools` | `list[str]` | `[]` | List of tool names the agent is permitted to use. An empty list means no tools. |
| `allowed_skills` | `list[str]` | `[]` | List of skill names this agent may use. Skills must exist in the skill registry. See [agent_skill.md](./agent_skill.md). |
| `allowed_agents` | `list[str]` | `[]` | List of agent IDs this agent may delegate to. Used for hierarchical agent setups. |
| `is_default` | `bool` | `false` | If `true`, this agent is pre-selected for new chat sessions. Only one agent should have this flag. |

### System prompt

The markdown body after the YAML frontmatter is the system prompt. It is stored as `system_prompt` in the blueprint and passed to the LLM as the initial system message.

## Search Paths

`AgentRegistry` resolves agent files from a list of `agent_search_paths` defined in the user's config. The default list:

```
[PACKAGE_ROOT / "agent/builtin_agents", .genesis/agents/]
```

- The first path is read-only — it ships built-in agents with the package.
- The last path is the user's private agent directory — writable, where user-created agents are saved.

When the registry loads, it iterates over all paths in order. Blueprints from later directories shadow earlier ones if they share the same filename stem. The file stem (filename without `.md`) is used as the agent ID.

## LLM Model Resolution

When loading a manifest, the registry looks up `model_name` from the frontmatter in the user's `Config.models` dictionary:

```python
[llm_config, provider_config] = self._get_llm_model_config(llm_model_name)
```

If `model_name` is empty, no LLM config is attached and the agent falls back to the global default. The resolved `llm_config` and `provider_config` are stored in the `AgentConfig` blueprint alongside the other fields.

The provider routing in `llm/_base.py` uses the provider name from the resolved config to decide whether to use LiteLLM or the Anthropic SDK.

## Loading and Validation

The registry loads all `.md` files in each search path. It parses the frontmatter with `python-frontmatter` and attempts to validate each manifest as an `AgentConfig`. Malformed manifests are skipped with a logged error rather than crashing the load process, so a single bad agent does not break the entire system.

## Creation via API

`POST /agents/` accepts an `AgentCreate` payload. If the model name is omitted, the user's default model is substituted. After validation, `AgentRegistry.add_agent()`:

1. Slugifies the `name` field to generate a filename (e.g., `"My Agent"` becomes `"my_agent.md"`)
2. Handles filename collisions by appending a UUID suffix
3. Writes the manifest to the user's agent directory
4. Reloads the registry to include the new agent

The manifest written to disk matches the same frontmatter + markdown body format.

## Editing via API

`PATCH /agents/{agent_id}` reads the existing `.md` file, applies the field updates to the frontmatter, and rewrites the file. The system prompt body can only be updated via the `system_prompt` field. On success the registry is reloaded.

## Deletion via API

`DELETE /agents/{agent_id}` removes the `.md` file. If the agent has `read_only: true` in the frontmatter, the delete raises a `403 Forbidden` instead.

## Key Files

| File | Role |
|---|---|
| `genesis-core/src/genesis_core/agent/agent_registry.py` | `AgentRegistry` — directory scanning, manifest loading, CRUD |
| `genesis-core/src/genesis_core/schemas.py` | `AgentConfig` Pydantic model |
| `genesis-core/src/genesis_core/agent/builtin_agents/*.md` | Built-in agent manifests shipped with the package |
| `genesis-server/src/genesis_server/routers/agents.py` | REST API endpoints for agent CRUD |
| `genesis-server/src/genesis_server/dependencies.py` | `get_agent_registry` — user-scoped `AgentRegistry` via DI |