"""System prompt factory — assembles prompt from modular fragments based on agent configuration."""

import logging

from pydantic import BaseModel, ConfigDict

from genesis_core.skill import SkillRegistry

from . import fragments

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool-to-skill mapping
# Maps tool names to their corresponding builtin skill names.
# ---------------------------------------------------------------------------

_TOOL_TO_SKILL = {
    "remember_this": "memory_skill",
    "search_memories": "memory_skill",
    "list_memories": "memory_skill",
    "get_memory": "memory_skill",
    "update_memory": "memory_skill",
    "delete_memory": "memory_skill",
    "rebuild_fts_index": "memory_skill",
    "search_tasks": "productivity_skill",
    "read_task": "productivity_skill",
    "search_projects": "productivity_skill",
    "read_project": "productivity_skill",
    "search_journals": "productivity_skill",
    "read_journal": "productivity_skill",
    "create_task": "productivity_skill",
    "create_project": "productivity_skill",
    "create_journal": "productivity_skill",
    "update_tasks": "productivity_skill",
    "update_project": "productivity_skill",
    "edit_journal": "productivity_skill",
    "read_file": "file_skill",
    "list_files": "file_skill",
    "write_file": "file_skill",
    "edit_file": "file_skill",
    "find_files": "file_skill",
    "delete_file": "file_skill",
    "move_file": "file_skill",
    "search_file_content": "file_skill",
    "web_search": "web_skill",
    "news_search": "web_skill",
    "fetch_web_page": "web_skill",
}


class BuildPromptConfig(BaseModel):
    """Configuration for building a system prompt."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    system_prompt: str  # The agent-specific role/instruction block from the .md file
    allowed_tools: list[str] = []  # Tool names from agent_config.allowed_tools
    interactive: bool = False  # Whether the agent is in interactive mode
    has_memory_db: bool = False  # True when memory_db_url is set
    has_user_db: bool = False  # True when user_db_url is set (productivity subsystem)
    has_working_directory: bool = False  # True when a working directory is provided
    allowed_skills: list[str] = []  # Skill names from agent_config.allowed_skills
    skill_registry: SkillRegistry | None = None  # SkillRegistry instance for resolving skill metadata
    agent_name: str = "unknown"  # Agent name for logging purposes


def _inject_missing_builtin_skills(config: BuildPromptConfig) -> list[str]:
    """Check for missing builtin skills and auto-inject them with a warning log.

    If an agent has tools that map to a builtin skill, but the skill is not listed
    in allowed_skills, the skill is injected automatically and a warning is logged.

    Returns the augmented skill list.
    """
    if not config.skill_registry:
        return list(config.allowed_skills)

    allowed_set = set(config.allowed_skills)
    auto_injected: list[str] = []
    tool_to_missing_skill: dict[str, str] = {}

    for tool in config.allowed_tools:
        skill = _TOOL_TO_SKILL.get(tool)
        if skill and skill not in allowed_set:
            auto_injected.append(skill)
            tool_to_missing_skill.setdefault(skill, tool)

    if auto_injected:
        unique_skills = list(dict.fromkeys(auto_injected))  # preserve order, dedupe
        logger.warning(
            "Agent '%s' has tools %s but is missing the corresponding skill(s) %s. "
            "Automatically injected for this session. Add these skills to the agent "
            "manifest's allowed_skills list.",
            config.agent_name,
            sorted(tool_to_missing_skill.values()),
            sorted(tool_to_missing_skill.keys()),
        )
        return list(config.allowed_skills) + unique_skills

    return list(config.allowed_skills)


def build_system_prompt(config: BuildPromptConfig) -> str:
    """Assemble the full system prompt from fragments based on agent configuration.

    The prompt is constructed from modular fragments. Only fragments relevant
    to the agent's tools and environment are included.
    """
    parts = []

    # 1. Base instruction — always included
    parts.append(fragments.BASE_INSTRUCTION)

    # 2. Skill instructions — included when read_skill is in the tool list
    if "read_skill" in config.allowed_tools:
        injected_skills = _inject_missing_builtin_skills(config)
        skills_to_show = injected_skills if injected_skills else config.allowed_skills

        skill_entries: list[str] = []
        if config.skill_registry and skills_to_show:
            for skill in skills_to_show:
                skill_config = config.skill_registry.get_skill(skill)
                if skill_config:
                    skill_entries.append(f"- **{skill_config.name}**: {skill_config.description}")

        skill_section = fragments.FRAGMENT_SKILL_INSTRUCTIONS.format(
            skill_entries="\n".join(skill_entries) if skill_entries else "(none)"
        )
        parts.append(skill_section)

    # 3. Agent-specific role description — always last, from the .md file

    persona_section = fragments.FRAGMENT_PERSONA.format(system_prompt=config.system_prompt)
    parts.append(persona_section)

    return "\n\n".join(parts)

