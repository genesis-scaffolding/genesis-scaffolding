"""Skill-related tool for agents to read skill manifests at runtime."""

from typing import Any

from .base import BaseTool
from .schema import ToolResult


class ActivateSkillTool(BaseTool):
    """Tool for loading a skill's full instructions into the clipboard.

    The skill_registry is injected by the agent harness at runtime via kwargs.
    """

    name = "activate_skill"
    description = "Load a skill's full instructions into the clipboard. Check the clipboard for the content, then follow the skill's instructions to carry out the task."
    parameters = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The name of the skill to read (e.g., 'writing_skill').",
            },
        },
        "required": ["skill_name"],
    }

    async def run(
        self,
        working_directory: Any,  # Path, injected by harness
        skill_name: str,
        skill_registry: Any = None,  # Injected by harness at runtime
        **kwargs: Any,
    ) -> ToolResult:
        if skill_registry is None:
            return ToolResult(
                status="error",
                tool_response="Skill registry is not available. Cannot read skills.",
                results_to_add_to_clipboard=[],
                files_to_add_to_clipboard=[],
                entities_to_track=[],
            )

        skill = skill_registry.get_skill(skill_name)
        if not skill:
            available = [s.name for s in skill_registry.get_all_skills()]
            available_str = ", ".join(available) if available else "none"
            return ToolResult(
                status="error",
                tool_response=f"Skill '{skill_name}' not found. Available skills: {available_str}.",
                results_to_add_to_clipboard=[],
                files_to_add_to_clipboard=[],
                entities_to_track=[],
            )

        content = f"## {skill.name}\n\n{skill.instructions}"
        return ToolResult(
            status="success",
            tool_response=f"Skill '{skill.name}' loaded. Full instructions are in the clipboard under the activate_skill tool result. Follow the instructions to carry out the task.",
            results_to_add_to_clipboard=[content],
            files_to_add_to_clipboard=[],
            entities_to_track=[],
        )