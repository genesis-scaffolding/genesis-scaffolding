# Agent Skills Architecture

## Overview

Skills are reusable capability manifests that agents can reference and access at runtime. A skill is defined in a Markdown file with YAML frontmatter. The frontmatter holds metadata (name, description, version), and the markdown body holds the skill's instructions.

The skill system follows the same architectural patterns as the agent registry:

- Skills are discovered from configurable search paths
- Multiple search paths support builtin vs user-defined skills
- A `SkillRegistry` provides in-memory lookup of skill blueprints
- Agents access skills via the `read_skill` tool at runtime

## Skill Manifest Format

Skills are Markdown files with YAML frontmatter:

```yaml
---
name: "Writing Skill"
description: "Guidelines for producing clear, concise written content"
version: "1.0"
---

# Writing Skill

You are a writing specialist. Your role is to help produce high-quality written content.

## Core Principles

1. **Clarity** — Use simple words and short sentences.
2. **Specificity** — Be concrete and precise.
...
```

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Display name. Used as the skill identifier in agent manifests. |
| `description` | `str` | `""` | Brief description shown to the LLM when listing available skills. |
| `version` | `str` | `"1.0"` | Version string for the skill definition. |

The markdown body after the closing `---` is the skill instructions. It is stored as `instructions` in the `SkillConfig` blueprint and returned in full when the agent calls `read_skill`.

## Search Paths

`SkillRegistry` resolves skill files from `settings.path.skill_search_paths`:

```
[PACKAGE_ROOT / "skill" / "builtin_skills", .genesis/skills/]
```

- First path is read-only — ships builtin skills with the package.
- Last path is the user's private skill directory — writable.

The file stem (filename without `.md`) is used as the skill name, for example `writing_skill.md` becomes `"writing_skill"`.

## Skill Registry

```python
class SkillRegistry:
    def __init__(self, settings: Config):
        self.skill_search_paths = settings.path.skill_search_paths
        self.blueprints: dict[str, SkillConfig] = {}
        self.load_all()

    def get_skill(self, name: str) -> SkillConfig | None
    def get_skills_by_names(self, names: list[str]) -> list[SkillConfig]
    def get_all_skills(self) -> list[SkillConfig]
```

The registry scans all search paths on initialization, parses `.md` files with frontmatter, and stores `SkillConfig` blueprints keyed by file stem.

## Agent Integration

### Agent Manifest

Agents reference skills via the `allowed_skills` field in their manifest:

```yaml
---
name: "Max"
description: "Max is a helpful AI assistant"
allowed_tools:
  - search_web
  - read_file
allowed_skills:
  - writing_skill
---

You are Max, a helpful AI assistant...
```

### System Prompt Injection

When an agent is created, `build_system_prompt()` receives the agent's `allowed_skills` list and the skill registry. If skills are present, it renders a skill list section into the system prompt:

```markdown
## Available Skills

The following specialized skills are available for you to use. Use the `read_skill` tool to load a skill's full instructions when you need it.

- **Writing Skill**: Guidelines for producing clear, concise written content
```

This gives the LLM awareness of available skills without embedding the full instructions. The agent can call `read_skill` to load the full content when needed.

### Skill Registry Pass-through

`AgentRegistry` owns a `SkillRegistry` instance:

```python
class AgentRegistry:
    def __init__(self, settings: Config):
        self.skill_registry = SkillRegistry(settings=settings)
        # ...

    def create_agent(self, ..., **overrides) -> Agent:
        return Agent(
            agent_config=instance_config,
            skill_registry=self.skill_registry,
            # ...
        )
```

The skill registry is stored on the `Agent` instance and passed to tools via kwargs during tool execution.

## Read Skill Tool

The `read_skill` tool fetches a skill's full instructions at runtime:

```python
class ReadSkillTool(BaseTool):
    name = "read_skill"
    parameters = {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "The name of the skill to read (e.g., 'writing_skill')."},
        },
        "required": ["skill_name"],
    }

    async def run(self, skill_name: str, skill_registry=None, **kwargs) -> ToolResult:
        # ...
```

### Tool Execution Flow

```
Agent._execute_tool_and_format(tool_id, "read_skill", {"skill_name": "writing_skill"}, working_directory):
    tool.run(
        working_directory=...,
        skill_registry=self.skill_registry,  # injected by harness
        skill_name="writing_skill",
        **kwargs,
    )
```

### Tool Result

On success, the tool returns the skill content:

- `tool_response`: Formatted markdown with skill title and instructions
- `results_to_add_to_clipboard`: Same content added to clipboard for persistence

On failure (skill not found or registry unavailable), returns an error with available skills listed.

## Key Files

| File | Role |
|---|---|
| `genesis-core/src/genesis_core/schemas.py` | `SkillConfig` and `AgentConfig.allowed_skills` |
| `genesis-core/src/genesis_core/configs.py` | `skill_search_paths` in `PathConfigs` |
| `genesis-core/src/genesis_core/skill/skill_registry.py` | `SkillRegistry` — discovery and lookup |
| `genesis-core/src/genesis_core/agent/agent_registry.py` | Owns `SkillRegistry`, passes to agents |
| `genesis-core/src/genesis_core/agent/agent.py` | Stores skill_registry, passes to tools |
| `genesis-core/src/genesis_core/prompts/builder.py` | Builds skill list section in system prompt |
| `genesis-tools/src/genesis_tools/skill.py` | `ReadSkillTool` |
| `genesis-tools/src/genesis_tools/registry.py` | Tool registration |
| `genesis-core/src/genesis_core/skill/builtin_skills/*.md` | Builtin skill manifests |

## See also

- [agent_manifests.md](./agent_manifests.md) — agent manifest format, `allowed_skills` field
- [agent_tool.md](./agent_tool.md) — tool execution lifecycle, framework-injected kwargs
- [developer_guides/adding_agent_skill.md](./developer_guides/adding_agent_skill.md) — how to add new skills