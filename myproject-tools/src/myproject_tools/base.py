from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .schema import ToolResult


class BaseTool(ABC):
    # We define these as class attributes with type hints
    # Subclasses can now simple assign 'name = "..."'
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def run(self, working_directory: Path, *args: Any, **kwargs: Any) -> ToolResult:
        """Execute logic and return a ToolResult data object."""
        pass

    def to_llm_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def _validate_path(
        self,
        working_directory: Path,
        path_str: str,
        must_exist: bool = True,
        should_be_dir: bool = False,
        should_be_file: bool = False,
    ) -> Path:
        """
        Internal utility to ensure a path is safe and valid.
        Returns a resolved Path object or raises ValueError with a message for the agent.
        """
        user_path = Path(path_str)
        # 1. Security: Don't allow absolute paths or escaping the working directory
        full_path = (working_directory / user_path).absolute()

        if not full_path.is_relative_to(working_directory.resolve()):
            raise ValueError(f"Access denied: '{path_str}' is outside the allowed working directory.")

        # 2. Existence check
        if must_exist and not full_path.exists():
            raise ValueError(f"Path does not exist: '{path_str}'")

        # 3. Type checks
        if should_be_dir and full_path.exists() and not full_path.is_dir():
            raise ValueError(f"Expected a directory, but found a file: '{path_str}'")

        if should_be_file and full_path.exists() and not full_path.is_file():
            raise ValueError(f"Expected a file, but found a directory: '{path_str}'")

        return full_path
