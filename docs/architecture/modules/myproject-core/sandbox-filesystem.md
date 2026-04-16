# Sandbox Filesystem

## Overview

The sandbox filesystem is a filesystem abstraction that enforces sandbox boundaries, ensuring all operations stay within a user's designated working directory. It is the single source of truth for file operations across the application (frontend API, agent tools, and CLI).

The abstraction is designed to be swappable — a future S3-backed implementation can replace `LocalSandboxFilesystem` without changing the calling code.

## Architecture

### `SandboxFilesystem` ABC

An abstract base class defining the interface for all sandbox filesystem operations:

```python
class SandboxFilesystem(ABC):
    @abstractmethod
    def resolve_path(self, relative_path: str) -> Path: ...

    @abstractmethod
    def list_directory(self, folder: str = ".") -> list[SandboxFileInfo]: ...

    @abstractmethod
    def read_file(self, relative_path: str) -> bytes: ...

    @abstractmethod
    def write_file(self, relative_path: str, content: bytes) -> SandboxFileInfo: ...

    @abstractmethod
    def delete_file(self, relative_path: str) -> None: ...

    @abstractmethod
    def create_directory(self, relative_path: str) -> SandboxFileInfo: ...

    @abstractmethod
    def get_file_info(self, relative_path: str) -> SandboxFileInfo: ...

    @abstractmethod
    def file_exists(self, relative_path: str) -> bool: ...

    @abstractmethod
    def get_subdirectories(self, parent_folder: str = ".") -> list[str]: ...

    @abstractmethod
    def delete_directory(self, relative_path: str) -> None: ...
```

All paths passed to methods are relative to the sandbox root. Implementations must enforce sandbox boundary checks to prevent path traversal attacks.

### `LocalSandboxFilesystem`

The concrete implementation using the local filesystem:

```python
class LocalSandboxFilesystem(SandboxFilesystem):
    def __init__(self, sandbox_root: Path, allow_symlinks_outside: bool = True) -> None:
        self._root = sandbox_root.resolve()
        self._allow_symlinks_outside = allow_symlinks_outside
```

## Security: Path Traversal Prevention

The `_resolve()` method handles path resolution and sandbox boundary enforcement:

1. **Join path**: `joined = self._root / relative_path`
2. **Check symlink**: `is_symlink = joined.is_symlink()` (before resolving)
3. **Resolve**: `full = joined.resolve()` — handles both `..` traversal and symlink targets
4. **Boundary check**: If resolved path escapes sandbox AND is not an allowed symlink, raise `ValueError`

```python
if not full.is_relative_to(self._root):
    if self._allow_symlinks_outside and is_symlink:
        return full  # Allow symlinks to external dirs
    raise ValueError(f"Traversal attempt detected: {relative_path}")
```

This ensures:
- `../../../etc/passwd` is blocked (not a symlink)
- Symlinks to external directories (e.g., Obsidian vault) are allowed when `allow_symlinks_outside=True`

## Symlink Handling

The `allow_symlinks_outside` flag defaults to `True` for self-hosted deployments. This allows users to symlink existing directories (like an Obsidian vault or code repositories) into their sandbox without the files being copied.

## Schema

### `SandboxFileInfo` Dataclass

The return type for all file operations:

```python
@dataclass
class SandboxFileInfo:
    relative_path: str   # Path relative to sandbox root (primary identifier)
    name: str            # Filename without path
    is_dir: bool = False
    size: int | None = None
    mime_type: str | None = None
    mtime: float | None = None
    created_at: datetime | None = None
```

**Note:** `relative_path` is used as the primary file identifier in URLs (base64url-encoded), not a database ID.

## Relationship to Workspace

The workflow workspace module (`myproject_core.workflow.workflow_workspace`) handles workflow job directories — creating isolated workspaces per job with `input/`, `internal/`, and `output/` subdirectories. The sandbox filesystem handles user-facing file operations in their persistent sandbox.

Future refactoring could have workspace use `SandboxFilesystem` internally instead of its own path logic, but for now they remain separate modules.

## Related Modules

- `myproject_core.schemas` — `SandboxFileInfo` dataclass definition
- `myproject_server.routers.files` — FastAPI endpoints using this abstraction
- `myproject_server.dependencies` — `get_user_workdir` for resolving user sandbox root
