"""System prompt factory — assembles prompt from modular fragments based on agent configuration."""

from pydantic import BaseModel, ConfigDict

from genesis_core.skill import SkillRegistry

from . import fragments


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


# ---------------------------------------------------------------------------
# Tool category detection helpers
# ---------------------------------------------------------------------------

_MEMORY_TOOL_NAMES = frozenset([
    "remember_this",
    "search_memories",
    "list_memories",
    "get_memory",
    "update_memory",
    "delete_memory",
    "rebuild_fts_index",
])

_PRODUCTIVITY_TOOL_NAMES = frozenset([
    "search_tasks",
    "read_task",
    "search_projects",
    "read_project",
    "search_journals",
    "read_journal",
    "create_task",
    "create_project",
    "create_journal",
    "update_tasks",
    "update_project",
    "edit_journal",
])

_FILE_TOOL_NAMES = frozenset([
    "read_file",
    "list_files",
    "write_file",
    "edit_file",
    "find_files",
    "delete_file",
    "move_file",
    "search_file_content",
])

_WEB_TOOL_NAMES = frozenset([
    "web_search",
    "news_search",
    "fetch_web_page",
])

_PDF_TOOL_NAMES = frozenset([
    "pdf_to_markdown",
])


def _has_memory_tools(tools: list[str]) -> bool:
    return bool(tools and not _MEMORY_TOOL_NAMES.isdisjoint(tools))


def _has_productivity_tools(tools: list[str]) -> bool:
    return bool(tools and not _PRODUCTIVITY_TOOL_NAMES.isdisjoint(tools))


def _has_file_tools(tools: list[str]) -> bool:
    return bool(tools and not _FILE_TOOL_NAMES.isdisjoint(tools))


def _has_web_tools(tools: list[str]) -> bool:
    return bool(tools and not _WEB_TOOL_NAMES.isdisjoint(tools))


def _has_pdf_tools(tools: list[str]) -> bool:
    return bool(tools and not _PDF_TOOL_NAMES.isdisjoint(tools))


# ---------------------------------------------------------------------------
# Main factory function
# ---------------------------------------------------------------------------

def build_system_prompt(config: BuildPromptConfig) -> str:
    """Assemble the full system prompt from fragments based on agent configuration.

    The prompt is constructed from modular fragments. Only fragments relevant
    to the agent's tools and environment are included.
    """
    parts = []

    # 1. Base instruction — always included
    parts.append(fragments.BASE_INSTRUCTION)

    # 2. Working directory / file tools
    if config.has_working_directory or _has_file_tools(config.allowed_tools):
        parts.append(fragments.FRAGMENT_WORKING_DIRECTORY)

    # 3. Memory guidance — included whenever memory tools are present
    if _has_memory_tools(config.allowed_tools):
        parts.append(fragments.FRAGMENT_MEMORY)

    # 5. Productivity subsystem — requires user DB AND productivity tools
    if config.has_user_db and _has_productivity_tools(config.allowed_tools):
        parts.append(fragments.FRAGMENT_PRODUCTIVITY_SYSTEM)

    # 6. Web tools
    if _has_web_tools(config.allowed_tools):
        parts.append(fragments.FRAGMENT_WEB_TOOLS)

    # 7. PDF tools
    if _has_pdf_tools(config.allowed_tools):
        parts.append(fragments.FRAGMENT_PDF_TOOLS)

    # 8. Skills — included when allowed_skills is populated
    if config.allowed_skills and config.skill_registry:
        skills = config.skill_registry.get_skills_by_names(config.allowed_skills)
        if skills:
            skills_text = "\n".join(f"- **{s.name}**: {s.description}" for s in skills)
            parts.append(f"""\n## Available Skills

The following specialized skills are available for you to use. Use the `read_skill` tool to load a skill's full instructions when you need it.

{skills_text}
""")

    # 9. Agent-specific role description — always last, from the .md file
    parts.append(config.system_prompt)

    return "\n\n".join(parts)
