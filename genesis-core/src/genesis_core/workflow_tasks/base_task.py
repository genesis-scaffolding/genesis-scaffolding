import ast
import asyncio
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..agent.agent_registry import AgentRegistry
from ..schemas import JobContext


### BASE TASK CLASS
class TaskParams(BaseModel):
    """Common schema for all workflow task parameters."""

    model_config = ConfigDict(extra="ignore")

    files_to_read: list[Path] = []

    sub_directory: str | None = None
    write_response_to_file: bool = True
    write_response_to_output: bool = False
    output_filename: str = ""
    output_filename_prefix: str = ""

    @model_validator(mode="before")
    @classmethod
    def pre_parse_all_jinja_strings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        for key, value in data.items():
            if isinstance(value, str):
                v = value.strip()

                # Check for booleans specifically because Jinja/JSON
                # often uses lowercase "true"/"false"
                if v.lower() == "true":
                    data[key] = True
                    continue
                if v.lower() == "false":
                    data[key] = False
                    continue
                if v.lower() == "none":
                    data[key] = None
                    continue

                # Use ast.literal_eval for numbers (int/float) and structures (list/dict)
                try:
                    # literal_eval handles "42", "3.14", "['a', 'b']", "{'a': 1}"
                    parsed = ast.literal_eval(v)
                    data[key] = parsed
                except (ValueError, SyntaxError):
                    # If it's a normal string (e.g., "Hello World"),
                    # literal_eval fails and we keep the original string.
                    continue
        return data

    @field_validator("files_to_read", mode="before")
    @classmethod
    def validate_to_path_list(cls, v: Any) -> list[Path]:
        if not v:
            return []

        # 1. Handle cases where 'v' is already a list (standard YAML list or Pydantic list)
        if isinstance(v, list):
            return cls._resolve_items_to_paths(v)

        # 2. Handle string inputs (Jinja resolutions or single string params)
        if isinstance(v, str):
            v = v.strip()

            # 2a. Remove "PosixPath(...)" or "WindowsPath(...)" wrappers from the string
            # This turns "[PosixPath('/path')]" into "['/path']"
            v = re.sub(r"(?:PosixPath|WindowsPath|Path)\(['\"](.+?)['\"]\)", r"'\1'", v)

            # 2b. If it's a stringified list "[...]"
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = ast.literal_eval(v)
                    if isinstance(parsed, list):
                        return cls._resolve_items_to_paths(parsed)
                    return [Path(str(parsed))]
                except (ValueError, SyntaxError):
                    # Manual fallback for comma-separated strings inside brackets
                    items = v.strip("[]").split(",")
                    return [Path(i.strip().strip("'\"")) for i in items if i.strip()]

            # 2c. Single string path
            return [Path(v)]

        return []

    @staticmethod
    def _resolve_items_to_paths(items: list) -> list[Path]:
        """Helper to ensure every item in a list is a Path object."""
        result = []
        for item in items:
            if not item:
                continue
            # If the item itself is a stringified list (nested accidentally)
            if isinstance(item, str) and item.startswith("["):
                # Recursive call to handle nested list strings
                result.extend(TaskParams._resolve_items_to_paths([item.strip("[]")]))
            else:
                result.append(Path(str(item).strip("'\" ")))
        return result


class TaskOutput(BaseModel):
    """Common schema for all workflow task output."""

    model_config = ConfigDict(extra="ignore")
    content: list[str]
    file_paths: list[Path] | None = None


TParams = TypeVar("TParams", bound=TaskParams)
TOutput = TypeVar("TOutput", bound=TaskOutput)


class BaseTask(ABC, Generic[TParams, TOutput]):
    params_model: type[TParams]
    output_model: type[TOutput]

    @abstractmethod
    async def run(self, context: JobContext, agent_registry: AgentRegistry, params: dict) -> TOutput:
        pass

    def resolve_input_file_paths(self, input_file_paths: list[Path], context: JobContext) -> list[Path]:
        """Resolve and dedup the input file paths provided to the workflow task"""
        resolved_files: list[Path] = []
        for path_str in input_file_paths:
            raw_path = Path(path_str)

            # If absolute, use as is; if relative, join with context.root
            if raw_path.is_absolute():
                base_path = raw_path
            else:
                base_path = (context.root / raw_path).resolve()

            if not base_path.exists():
                # You can choose to throw or log; following your previous pattern:
                raise FileNotFoundError(f"Resolved path does not exist: {base_path}")

            # 2. Directory vs File Handling
            if base_path.is_dir():
                # Recursively find all files in the directory
                for item in base_path.rglob("*"):
                    if item.is_file():
                        resolved_files.append(item.absolute())
            else:
                resolved_files.append(base_path.absolute())

        unique_files = list(set(resolved_files))
        return unique_files

    async def write_content_to_files(
        self,
        content: list[str],
        context: JobContext,
        output_filename: str,
        output_filename_prefix: str,
        write_response_to_output: bool,
        extension: str = "md",
        sub_directory: str | None = None,
    ) -> list[Path]:
        # Encapsulate logic in a synchronous inner function
        def _sync_write_operation():
            def _get_file_name(
                content: list[str],
                index: int,
                output_filename: str,
                output_filename_prefix: str,
                extension: str,
            ):
                if len(content) == 1:
                    if output_filename:
                        return output_filename
                    return f"{type(self)}_output.{extension}"
                return f"{output_filename_prefix}_{index}.{extension}"

            # Determine target directories
            target_dirs: list[Path] = []
            sub_dir = sub_directory or ""

            # Blocking IO: mkdir
            internal_dir = context.internal / sub_dir
            internal_dir.mkdir(parents=True, exist_ok=True)
            target_dirs.append(internal_dir)

            if write_response_to_output:
                # Blocking IO: mkdir
                output_dir = context.output / sub_dir
                output_dir.mkdir(parents=True, exist_ok=True)
                target_dirs.append(output_dir)

            # Write content items to files
            all_written_paths: list[Path] = []
            for i, content_item in enumerate(content):
                filename = _get_file_name(
                    content=content,
                    index=i,
                    output_filename=output_filename,
                    output_filename_prefix=output_filename_prefix,
                    extension=extension,
                )

                for target_dir in target_dirs:
                    target_file = target_dir / filename
                    # Blocking IO: write_text
                    target_file.write_text(content_item, encoding="utf-8")
                    all_written_paths.append(target_file)

            return all_written_paths

        # Run the sync wrapper in a thread
        # This releases the event loop immediately so FastAPI can serve the Redirect/GET request
        return await asyncio.to_thread(_sync_write_operation)

    async def link_or_copy_to_output(
        self,
        context: JobContext,
        internal_file_paths: list[Path],
        output_filename: str,
        output_filename_prefix: str,
        sub_directory: str | None = None,
    ) -> list[Path]:
        """Utility to expose internally written files to the output directory.
        Tries to symlink first, falls back to copying if symlinking fails.
        """

        def _sync_link_operation():
            target_output_paths: list[Path] = []

            # 1. Determine and create the target directory
            sub_dir = sub_directory or ""
            target_dir = context.output / sub_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            # 2. Process each file
            for _i, src_path in enumerate(internal_file_paths):
                if not src_path.exists():
                    continue

                # Determine target filename logic
                if len(internal_file_paths) == 1 and output_filename:
                    dest_filename = output_filename
                else:
                    # Prefix + existing filename as requested
                    dest_filename = f"{output_filename_prefix}{src_path.name}"

                dest_path = target_dir / dest_filename

                # 3. Perform Symlink or Copy
                # Remove existing file/link if it exists to avoid FileExistsError
                if dest_path.exists() or dest_path.is_symlink():
                    dest_path.unlink()

                try:
                    # Attempt symlink (requires absolute paths usually for reliability)
                    dest_path.symlink_to(src_path.absolute())
                except (OSError, NotImplementedError):
                    # Fallback to copy if symlink fails (e.g., cross-device or permissions)
                    shutil.copy2(src_path, dest_path)

                target_output_paths.append(dest_path)

            return target_output_paths

        # Run the blocking IO in a separate thread
        return await asyncio.to_thread(_sync_link_operation)
