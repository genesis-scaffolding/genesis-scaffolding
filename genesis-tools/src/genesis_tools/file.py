import asyncio
from pathlib import Path
from typing import Any

from genesis_tools.base import BaseTool
from genesis_tools.schema import ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = (
        "Reads the content of a file and adds it to your clipboard. "
        "Use this when you need to examine the code or data in a specific file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file you want to read, relative to the current working directory.",
            },
        },
        "required": ["file_path"],
    }

    async def run(self, working_directory: Path, file_path: str, **kwargs: Any) -> ToolResult:
        try:
            # Validate the path is safe and exists
            validated_path = self._validate_path(
                working_directory, file_path, must_exist=True, should_be_file=True,
            )

            # Note: We don't read the file here.
            # We return the path to the harness via 'files_to_add_to_clipboard'.
            return ToolResult(
                status="success",
                tool_response=f"File '{file_path}' has been read and added to your clipboard.",
                files_to_add_to_clipboard=[validated_path],
            )

        except ValueError as e:
            # Catch validation errors (access denied, file not found, etc.)
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            # Catch unexpected system errors (e.g., permission issues at the OS level)
            return ToolResult(
                status="error",
                tool_response=f"An unexpected error occurred while trying to read '{file_path}': {e!s}",
            )


class ListFilesTool(BaseTool):
    name = "list_files"
    description = (
        "Lists files and directories in a tree-like structure up to 2 levels deep. "
        "Helps you understand the project structure and locate specific files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The directory to list, relative to the working directory. Defaults to '.' (root).",
                "default": ".",
            },
        },
    }

    # Directories we should almost always ignore to save tokens and avoid noise
    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".vscode"}

    async def run(self, working_directory: Path, path: str = ".", **kwargs: Any) -> ToolResult:
        try:
            root_path = self._validate_path(working_directory, path, must_exist=True, should_be_dir=True)

            tree_lines = [f"Listing for directory: {path}"]
            item_count = 0
            max_items = 250
            truncated = False

            # We use os.walk or rglob? rglob is easier for depth control
            # But let's build a manual recursive logic to handle IGNORE_DIRS efficiently
            def build_tree(current_dir: Path, current_depth: int, prefix: str = ""):
                nonlocal item_count, truncated
                if current_depth > 2 or item_count >= max_items:
                    if item_count >= max_items:
                        truncated = True
                    return

                # Sort to ensure deterministic output (better for caching)
                try:
                    entries = sorted(
                        current_dir.iterdir(), key=lambda x: (x.is_file(), x.name.lower()),
                    )
                except PermissionError:
                    tree_lines.append(f"{prefix}└── [Permission Denied]")
                    return

                for i, entry in enumerate(entries):
                    if item_count >= max_items:
                        truncated = True
                        break

                    if entry.name in self.IGNORE_DIRS:
                        continue

                    item_count += 1
                    is_last = i == len(entries) - 1
                    connector = "└── " if is_last else "├── "

                    tree_lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")

                    if entry.is_dir():
                        extension = "    " if is_last else "│   "
                        build_tree(entry, current_depth + 1, prefix + extension)

            build_tree(root_path, 1)

            if truncated:
                tree_lines.append("... [List truncated: too many items] ...")

            tree_output = "\n".join(tree_lines)

            return ToolResult(
                status="success",
                tool_response=f"Directory listing for '{path}' has been added to your clipboard.",
                results_to_add_to_clipboard=[tree_output],
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Error listing directory: {e!s}")


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Creates a NEW file in the working directory. "
        "IMPORTANT: This tool is strictly for creating new files only. It is NOT allowed to overwrite or modify existing files. "
        "If you need to update or change a file that already exists, you must use the edit tool instead. "
        "After successful writing, the file content will be added to your clipboard."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path, including the name of the new file, relative to the working directory.",
            },
            "content": {
                "type": "string",
                "description": "The full content to write into the file.",
            },
        },
        "required": ["file_path", "content"],
    }

    async def run(self, working_directory: Path, file_path: str, content: str, **kwargs: Any) -> ToolResult:
        try:
            # 1. Validate path
            validated_path = self._validate_path(
                working_directory, file_path, must_exist=False, should_be_file=True,
            )

            # 2. Check if file already exists to prevent overwriting
            if validated_path.exists():
                error_msg = (
                    f"Error: The file '{file_path}' already exists. "
                    f"The 'write_file' tool cannot be used to overwrite files. "
                    f"Please use the appropriate edit tool to modify this existing file."
                )
                return ToolResult(status="error", tool_response=error_msg)

            # 3. Perform I/O in a thread to avoid blocking the event loop
            def perform_write():
                # Ensure parent directories exist
                validated_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the content
                validated_path.write_text(content, encoding="utf-8")

            await asyncio.to_thread(perform_write)

            # 4. Return success
            response_message = "File write operation completed successfully.\nResults:\n"
            response_message += f"- The content was written to a NEW file at: '{file_path}'.\n"

            return ToolResult(
                status="success",
                tool_response=response_message,
                files_to_add_to_clipboard=[validated_path],
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to write file '{file_path}': {e!s}")


class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Replaces a single specific block of text in a file with new text. "
        "Use this tool to add or replace content of an existing file."
        "After succcesful editing the actual file in the working directory, the latest content of the file would be added to your clipboard for future tasks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file, relative to the working directory.",
            },
            "old_str": {
                "type": "string",
                "description": "The exact block of text you want to replace. It must match the file content EXACTLY, including identation.",
            },
            "new_str": {
                "type": "string",
                "description": "The new text that will replace 'old_str'.",
            },
        },
        "required": ["file_path", "old_str", "new_str"],
    }

    async def run(
        self, working_directory: Path, file_path: str, old_str: str, new_str: str, **kwargs: Any,
    ) -> ToolResult:
        try:
            # 1. Validate path
            validated_path = self._validate_path(
                working_directory, file_path, must_exist=True, should_be_file=True,
            )

            # 2. Perform editing logic
            def apply_edit():
                content = validated_path.read_text(encoding="utf-8")

                # Check for existence
                occurrence_count = content.count(old_str)

                if occurrence_count == 0:
                    # Provide a helpful error if the model messed up the copy-paste
                    raise ValueError(
                        f"Could not find the old string you specified: {old_str}"
                        f"Please check the file content of {file_path} on your clipboard and ensure your old string "
                        "matches the indentation and characters exactly."
                        "Write smaller old string could help.",
                    )

                if occurrence_count > 1:
                    # Provide a helpful error if the string isn't unique enough
                    raise ValueError(
                        f"Found {occurrence_count} occurrences of old string in '{file_path}'. "
                        "Please include more surrounding lines in old string to make the match unique.",
                    )

                # Perform the replacement
                new_content = content.replace(old_str, new_str)
                validated_path.write_text(new_content, encoding="utf-8")

            # Run disk I/O in a separate thread
            await asyncio.to_thread(apply_edit)

            # 3. Return success and trigger a clipboard refresh
            response_message = (
                f"File edit operation **completed successfully on the file {file_path}**\n"
                "The new version of the file has been added to the clipboard. Compare the old and the new version to verify the file edit task."
            )
            return ToolResult(
                status="success",
                tool_response=response_message,
                files_to_add_to_clipboard=[validated_path],
            )

        except ValueError as e:
            # Return validation errors as tool output so the agent can retry
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(
                status="error",
                tool_response=f"An unexpected error occurred while editing '{file_path}': {e!s}",
            )


class FindFilesTool(BaseTool):
    name = "find_files"
    description = (
        "Search for files by name pattern (e.g., '*.py', 'test_*.py', 'auth'). "
        "The search is recursive and starts from the specified directory."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The glob pattern to search for (e.g., 'database.py' or '*.css').",
            },
            "search_dir": {
                "type": "string",
                "description": "The directory to start the search from, relative to the working directory. Defaults to root.",
                "default": ".",
            },
        },
        "required": ["pattern"],
    }

    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

    async def run(
        self, working_directory: Path, pattern: str, search_dir: str = ".", **kwargs: Any,
    ) -> ToolResult:
        try:
            root_path = self._validate_path(
                working_directory, search_dir, must_exist=True, should_be_dir=True,
            )

            def search():
                matches = []
                # Walk through directories, skipping the ignored ones
                for path in root_path.rglob(pattern):
                    # Check if any part of the path is in IGNORE_DIRS
                    if any(part in self.IGNORE_DIRS for part in path.parts):
                        continue

                    if path.is_file():
                        # Return path relative to the working directory for the agent's convenience
                        matches.append(str(path.relative_to(working_directory)))

                    if len(matches) >= 50:
                        break
                return matches

            results = await asyncio.to_thread(search)

            if not results:
                return ToolResult(
                    status="success",
                    tool_response=f"No files matching '{pattern}' were found in '{search_dir}'.",
                )

            output = f"Found {len(results)} matches for '{pattern}':\n- " + "\n- ".join(results)
            if len(results) >= 50:
                output += "\n\n... (Limit reached, some results may be hidden)"

            return ToolResult(
                status="success",
                tool_response=f"Search results for '{pattern}' added to your clipboard.",
                results_to_add_to_clipboard=[output],
            )

        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e!s}")


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a specific file. Use this for cleanup or removing unnecessary code."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to delete, relative to the working directory.",
            },
        },
        "required": ["file_path"],
    }

    async def run(self, working_directory: Path, file_path: str, **kwargs: Any) -> ToolResult:
        try:
            # Validate path (must exist and must be a file)
            validated_path = self._validate_path(
                working_directory, file_path, must_exist=True, should_be_file=True,
            )

            def perform_delete():
                validated_path.unlink()

            await asyncio.to_thread(perform_delete)

            return ToolResult(
                status="success",
                tool_response=f"Successfully deleted file '{file_path}'.",
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=str(e))
        except Exception as e:
            return ToolResult(
                status="error", tool_response=f"Failed to delete file '{file_path}': {e!s}",
            )


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Moves or renames a file. Can also be used to move a file into a new directory."
    parameters = {
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "The current path of the file.",
            },
            "destination_path": {
                "type": "string",
                "description": "The new path or name for the file.",
            },
        },
        "required": ["source_path", "destination_path"],
    }

    async def run(
        self, working_directory: Path, source_path: str, destination_path: str, **kwargs: Any,
    ) -> ToolResult:
        try:
            src = self._validate_path(working_directory, source_path, must_exist=True, should_be_file=True)
            dst = self._validate_path(working_directory, destination_path, must_exist=False)

            if dst.exists():
                return ToolResult(
                    status="error", tool_response=f"Destination '{destination_path}' already exists.",
                )

            def perform_move():
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.rename(dst)

            await asyncio.to_thread(perform_move)

            return ToolResult(
                status="success",
                tool_response=f"Moved '{source_path}' to '{destination_path}'.",
                files_to_add_to_clipboard=[dst],  # Refresh clipboard with the new path on the next step
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Move failed: {e!s}")


class SearchFileContentTool(BaseTool):
    name = "search_file_content"
    description = "Searches for a specific string within all files in a directory (recursive)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text string to search for.",
            },
            "search_dir": {
                "type": "string",
                "description": "Directory to search in. Defaults to root.",
                "default": ".",
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob pattern to filter files (e.g., '*.py').",
                "default": "*",
            },
        },
        "required": ["query"],
    }

    IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

    async def run(
        self,
        working_directory: Path,
        query: str,
        search_dir: str = ".",
        file_pattern: str = "*",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            root_path = self._validate_path(
                working_directory, search_dir, must_exist=True, should_be_dir=True,
            )

            def perform_search():
                matches = []
                for path in root_path.rglob(file_pattern):
                    if any(part in self.IGNORE_DIRS for part in path.parts) or not path.is_file():
                        continue

                    try:
                        with open(path, encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if query in line:
                                    rel_path = path.relative_to(working_directory)
                                    matches.append(f"{rel_path}:{i}: {line.strip()}")
                                if len(matches) >= 100:
                                    return matches, True
                    except Exception:
                        continue  # Skip files that can't be read
                return matches, False

            results, truncated = await asyncio.to_thread(perform_search)

            if not results:
                return ToolResult(
                    status="success", tool_response=f"No matches found for '{query}' in '{search_dir}'.",
                )

            output = f"Search results for '{query}':\n" + "\n".join(results)
            if truncated:
                output += "\n\n... (Too many matches, results truncated)"

            return ToolResult(
                status="success",
                tool_response="Search results added to your clipboard.",
                results_to_add_to_clipboard=[output],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e!s}")
