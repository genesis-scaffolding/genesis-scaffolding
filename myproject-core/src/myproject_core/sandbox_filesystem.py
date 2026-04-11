"""Sandboxed filesystem abstraction.

This module provides a filesystem abstraction that enforces sandbox boundaries,
ensuring all operations stay within a user's designated working directory.
It is the single source of truth for file operations across the application
(frontend API, agent tools, and CLI).

The abstraction is designed to be swappable — a future S3-backed implementation
can replace LocalSandboxFilesystem without changing the calling code.
"""

import mimetypes
import os
import shutil
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from .schemas import SandboxFileInfo


class SandboxFilesystem(ABC):
    """Abstract interface for sandboxed filesystem operations.

    All paths passed to methods are relative to the sandbox root.
    Implementations must enforce sandbox boundary checks to prevent
    path traversal attacks.
    """

    @abstractmethod
    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path to an absolute path within the sandbox.

        Args:
            relative_path: Path relative to sandbox root.

        Returns:
            The absolute Path object.

        Raises:
            ValueError: If the path escapes the sandbox (traversal attempt).
        """

    @abstractmethod
    def list_directory(self, folder: str = ".") -> list[SandboxFileInfo]:
        """List files and subdirectories in a folder.

        Args:
            folder: Folder relative to sandbox root. Defaults to "." (root).

        Returns:
            List of SandboxFileInfo objects for entries in the directory.
            Returns empty list if folder does not exist or is not a directory.
        """

    @abstractmethod
    def read_file(self, relative_path: str) -> bytes:
        """Read file contents as bytes.

        Args:
            relative_path: Path to the file relative to sandbox root.

        Returns:
            File contents as bytes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path is a directory.
        """

    @abstractmethod
    def write_file(self, relative_path: str, content: bytes) -> SandboxFileInfo:
        """Create or overwrite a file.

        Creates parent directories if they do not exist.

        Args:
            relative_path: Path to the file relative to sandbox root.
            content: File contents as bytes.

        Returns:
            SandboxFileInfo for the written file.
        """

    @abstractmethod
    def delete_file(self, relative_path: str) -> None:
        """Delete a file.

        Args:
            relative_path: Path to the file relative to sandbox root.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path is a directory.
        """

    @abstractmethod
    def create_directory(self, relative_path: str) -> SandboxFileInfo:
        """Create a directory.

        Creates parent directories if they do not exist.

        Args:
            relative_path: Path to the directory relative to sandbox root.

        Returns:
            SandboxFileInfo for the created directory.
        """

    @abstractmethod
    def get_file_info(self, relative_path: str) -> SandboxFileInfo:
        """Get file or directory info.

        Args:
            relative_path: Path relative to sandbox root.

        Returns:
            SandboxFileInfo for the file or directory.

        Raises:
            FileNotFoundError: If the path does not exist.
        """

    @abstractmethod
    def file_exists(self, relative_path: str) -> bool:
        """Check if a file or directory exists.

        Args:
            relative_path: Path relative to sandbox root.

        Returns:
            True if the path exists, False otherwise.
        """

    @abstractmethod
    def get_subdirectories(self, parent_folder: str = ".") -> list[str]:
        """Get all subdirectory paths under a parent folder.

        Returns full relative paths (not just names) of immediate subdirectories.
        For example, if parent_folder is "." and it contains "docs/" and "data/",
        returns ["docs", "data"].

        Args:
            parent_folder: Parent folder relative to sandbox root. Defaults to ".".

        Returns:
            List of relative paths of subdirectories, sorted alphabetically.
            Returns empty list if parent_folder does not exist or has no subdirectories.
        """

    @abstractmethod
    def delete_directory(self, relative_path: str) -> None:
        """Delete an empty directory.

        Args:
            relative_path: Path to the directory relative to sandbox root.

        Raises:
            FileNotFoundError: If the directory does not exist.
            ValueError: If the path is a file, not a directory.
            OSError: If the directory is not empty.
        """

    @abstractmethod
    def move_file(self, source_relative_path: str, dest_relative_path: str) -> SandboxFileInfo:
        """Move a file to a new location within the sandbox.

        Only files are supported. Directory moves are not supported in this version.

        Args:
            source_relative_path: Current path relative to sandbox root.
            dest_relative_path: Target path relative to sandbox root.

        Returns:
            SandboxFileInfo for the moved file at its new location.

        Raises:
            FileNotFoundError: If the source does not exist.
            ValueError: If dest_relative_path escapes the sandbox or source is a directory.
        """


class LocalSandboxFilesystem(SandboxFilesystem):
    """Local filesystem implementation using pathlib.

    This implementation uses the local filesystem for all operations.
    It is the default implementation for self-hosted deployments.
    """

    def __init__(self, sandbox_root: Path, allow_symlinks_outside: bool = True) -> None:
        """Initialize with a sandbox root directory.

        Args:
            sandbox_root: The root directory for this sandbox.
                All file operations will be confined to this directory.
            allow_symlinks_outside: If True, allows symlinks inside the sandbox
                to point outside the sandbox (e.g., to user's Obsidian vault).
                This is useful for self-hosted deployments where users want
                to integrate their existing files. Defaults to True.
        """
        self._root = sandbox_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._allow_symlinks_outside = allow_symlinks_outside

    def _resolve(self, relative_path: str) -> Path:
        """Enforce sandbox boundary and return absolute path.

        Args:
            relative_path: Path relative to sandbox root.

        Returns:
            The resolved absolute path.

        Raises:
            ValueError: If the path escapes the sandbox.
        """
        joined = self._root / relative_path

        # Normalize path: resolve . and .. components without following symlinks
        normalized = Path(os.path.normpath(os.path.abspath(str(joined))))

        # Check if normalized path is within sandbox
        if not normalized.is_relative_to(self._root):
            raise ValueError(f"Traversal attempt detected: {relative_path}")

        # Path is inside sandbox - check if it's a symlink that escapes
        if joined.is_symlink():
            resolved = joined.resolve()
            if not resolved.is_relative_to(self._root) and not self._allow_symlinks_outside:
                raise ValueError(f"Traversal attempt detected: {relative_path}")

        return normalized

    def _entry_to_file_info(self, entry: Path) -> SandboxFileInfo:
        """Convert a pathlib entry to SandboxFileInfo."""
        stat = entry.stat()
        rel = entry.relative_to(self._root)
        return SandboxFileInfo(
            relative_path=str(rel),
            name=entry.name,
            is_dir=entry.is_dir(),
            size=stat.st_size if entry.is_file() else None,
            mime_type=mimetypes.guess_type(entry.name)[0] if entry.is_file() else None,
            mtime=stat.st_mtime,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
        )

    def resolve_path(self, relative_path: str) -> Path:
        return self._resolve(relative_path)

    def list_directory(self, folder: str = ".") -> list[SandboxFileInfo]:
        target = self._resolve(folder)
        if not target.is_dir():
            return []

        results = []
        for entry in target.iterdir():
            results.append(self._entry_to_file_info(entry))
        return results

    def read_file(self, relative_path: str) -> bytes:
        path = self._resolve(relative_path)
        if not path.is_file():
            if not path.exists():
                raise FileNotFoundError(f"File not found: {relative_path}")
            raise ValueError(f"Path is a directory, not a file: {relative_path}")
        return path.read_bytes()

    def write_file(self, relative_path: str, content: bytes) -> SandboxFileInfo:
        path = self._resolve(relative_path)
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return self._entry_to_file_info(path)

    def delete_file(self, relative_path: str) -> None:
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        if not path.is_file():
            raise ValueError(f"Path is a directory, not a file: {relative_path}")
        path.unlink()

    def create_directory(self, relative_path: str) -> SandboxFileInfo:
        path = self._resolve(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return self._entry_to_file_info(path)

    def get_file_info(self, relative_path: str) -> SandboxFileInfo:
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {relative_path}")
        return self._entry_to_file_info(path)

    def file_exists(self, relative_path: str) -> bool:
        try:
            path = self._resolve(relative_path)
            return path.exists()
        except ValueError:
            # Path traversal attempt means it doesn't exist in our sandbox
            return False

    def get_subdirectories(self, parent_folder: str = ".") -> list[str]:
        target = self._resolve(parent_folder)
        if not target.is_dir():
            return []

        subdirs: set[str] = set()
        for entry in target.iterdir():
            if entry.is_dir():
                rel = entry.relative_to(self._root)
                subdirs.add(str(rel))
        return sorted(subdirs)

    def delete_directory(self, relative_path: str) -> None:
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {relative_path}")
        if not path.is_dir():
            raise ValueError(f"Path is a file, not a directory: {relative_path}")
        path.rmdir()

    def move_file(self, source_relative_path: str, dest_relative_path: str) -> SandboxFileInfo:
        src = self._resolve(source_relative_path)
        dst = self._resolve(dest_relative_path)

        if not src.exists():
            raise FileNotFoundError(f"Source not found: {source_relative_path}")

        # Only files are supported — directories must use agent
        if src.is_dir():
            raise ValueError("Directory move is not supported. Use the agent to move directories.")

        # Prevent moving into own subtree (no-op check)
        try:
            dst.relative_to(src)
            raise ValueError("Cannot move a file into itself")
        except ValueError:
            pass  # Not a subdirectory, OK

        # Detect name collision: refuse to overwrite
        if dst.exists():
            raise ValueError(f"Destination already exists: {dest_relative_path}")

        # Create parent dirs if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Use shutil.move for cross-filesystem support
        shutil.move(str(src), str(dst))

        return self._entry_to_file_info(dst)
