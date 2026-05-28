# Agent Skills Architecture

## Overview

Skills are reusable capability manifests that agents can reference and access at runtime. A skill is defined in a Markdown file with YAML frontmatter. The frontmatter holds metadata (name, description, version), and the markdown body holds the skill's instructions.

The skill system follows the same architectural patterns as the agent registry:

- Skills are discovered from configurable search paths
- Multiple search paths support builtin vs user-defined skills
- A `SkillRegistry` provides in-memory lookup of skill blueprints
- Agents access skills via the `activate_skill` tool at runtime

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

1. **Clarity** - Use simple words and short sentences.
2. **Specificity** - Be concrete and precise.
...
```

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Display name. Used as the skill identifier in agent manifests. |
| `description` | `str` | `""` | Brief description shown to the LLM when listing available skills. This field should state the trigger condition - when should the agent call `activate_skill` to load this skill? |
| `version` | `str` | `"1.0"` | Version string for the skill definition. |

The markdown body after the closing `---` is the skill instructions. It is stored as `instructions` in the `SkillConfig` blueprint and returned in full when the agent calls `activate_skill`.

## Search Paths

`SkillRegistry` resolves skill files from `settings.path.skill_search_paths`:

```
[PACKAGE_ROOT / "skill" / "builtin_skills", .genesis/skills/]
```

- First path is read-only - ships builtin skills with the package.
- Last path is the user's private skill directory - writable.

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

## Builtin Skills

The following builtin skills are available:

| Skill | Trigger |
|---|---|
| `memory_skill` | User references something from the past, a preference, a habit, or a previous conversation |
| `productivity_skill` | User asks about tasks, projects, calendar, agenda, plans, or journal entries |
| `web_skill` | User asks about current events, news, or factual information needing web search |
| `file_skill` | User asks to read, write, edit, list, search, or organize files in the working directory |

These skills are extracted from the previous prompt fragment system and migrated into skill manifests. Each builtin skill's manifest lives in `genesis-core/src/genesis_core/skill/builtin_skills/`.

## Agent Integration

### Prerequisite: The `activate_skill` Tool

**The `activate_skill` tool must be in the agent's `allowed_tools` list for the skill system to function.** Without it, the skill section is not injected into the system prompt and the agent cannot load skill instructions at runtime.

> Note: This is a temporary friction. In a future version, `activate_skill` will be injected automatically when `allowed_skills` is populated, removing the need to add it manually.

### Agent Manifest

Agents reference skills via the `allowed_skills` field in their manifest:

```yaml
---
name: "Max"
description: "Max is a helpful AI assistant"
allowed_tools:
  - read_file
  - search_web
  - activate_skill
allowed_skills:
  - writing_skill
---

You are Max, a helpful AI assistant...
```

### System Prompt Injection

When an agent is created, `build_system_prompt()` assembles the system prompt in this order:

1. `BASE_INSTRUCTION` - always included
2. Skill instructions fragment - included only when `activate_skill` is in `allowed_tools`
3. Agent manifest system prompt - the role description from the `.md` file

The skill instructions fragment tells the agent:

- What skills are and when to call `activate_skill`
- Which builtin skills are available and what triggers each one
- Which skills are active for this session (from `allowed_skills` plus auto-injected skills)

```markdown
## Skills

You have access to **skills** - specialized instruction sets that tell you how to handle specific types of requests.

**When your conversation or task aligns with a skill's trigger, call `activate_skill` immediately and follow its instructions.**

The skills you have access to in this session are:

- **Writing Skill**: Guidelines for producing clear, concise written content
```

### Auto-injection of Missing Builtin Skills

When `activate_skill` is in the tool list, `build_system_prompt()` checks whether the agent's tools map to any builtin skills that are not already in `allowed_skills`. If so, those skills are automatically added to the session skill list and a warning is logged:

```
Agent 'Max' has tools ['read_file', 'remember_this'] but is missing the
corresponding skill(s) ['file_skill', 'memory_skill']. Automatically
injected for this session. Add these skills to the agent manifest's
allowed_skills list.
```

This prevents the agent from having powerful tools without the guidance to use them correctly. The fix is to add the missing skill names to the agent manifest's `allowed_skills` list.

### Tool-to-Skill Mapping

The following tool names trigger auto-injection of the corresponding builtin skill:

| Skill | Triggering Tools |
|---|---|
| `memory_skill` | `remember_this`, `search_memories`, `list_memories`, `get_memory`, `update_memory`, `delete_memory`, `rebuild_fts_index` |
| `productivity_skill` | `search_tasks`, `read_task`, `search_projects`, `read_project`, `search_journals`, `read_journal`, `create_task`, `create_project`, `create_journal`, `update_tasks`, `update_project`, `edit_journal` |
| `file_skill` | `read_file`, `list_files`, `write_file`, `edit_file`, `find_files`, `delete_file`, `move_file`, `search_file_content` |
| `web_skill` | `web_search`, `news_search`, `fetch_web_page` |

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

## Activate Skill Tool

The `activate_skill` tool fetches a skill's full instructions at runtime:

```python
class ActivateSkillTool(BaseTool):
    name = "activate_skill"
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
Agent._execute_tool_and_format(tool_id, "activate_skill", {"skill_name": "writing_skill"}, working_directory):
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
| `genesis-core/src/genesis_core/skill/skill_registry.py` | `SkillRegistry` - discovery and lookup |
| `genesis-core/src/genesis_core/agent/agent_registry.py` | Owns `SkillRegistry`, passes to agents |
| `genesis-core/src/genesis_core/agent/agent.py` | Stores skill_registry, passes to tools |
| `genesis-core/src/genesis_core/prompts/builder.py` | Builds skill section; handles auto-injection |
| `genesis-core/src/genesis_core/prompts/fragments.py` | `BASE_INSTRUCTION` and `FRAGMENT_SKILL_INSTRUCTIONS` |
| `genesis-tools/src/genesis_tools/skill.py` | `ActivateSkillTool` |
| `genesis-tools/src/genesis_tools/registry.py` | Tool registration |
| `genesis-core/src/genesis_core/skill/builtin_skills/*.md` | Builtin skill manifests |

## See also

- [agent_manifests.md](./agent_manifests.md) - agent manifest format, `allowed_skills` field
- [agent_tool.md](./agent_tool.md) - tool execution lifecycle, framework-injected kwargs
- [developer_guides/adding_agent_skill.md](./developer_guides/adding_agent_skill.md) - how to add new skills