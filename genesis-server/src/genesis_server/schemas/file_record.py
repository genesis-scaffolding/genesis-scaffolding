from pydantic import BaseModel


class SandboxFileRead(BaseModel):
    """API response schema for file read operations.
    Replicates the fields from SandboxFileInfo in genesis_core.schemas.
    """

    relative_path: str
    name: str
    is_dir: bool = False
    size: int | None = None
    mime_type: str | None = None
    mtime: float | None = None
    created_at: str | None = None


class FileUploadResponse(BaseModel):
    message: str
    file: SandboxFileRead


class FileMoveRequest(BaseModel):
    source_paths: list[str]  # List of relative paths to move
    destination_folder: str  # Target folder (relative path, "." for root)


class FileMoveResponse(BaseModel):
    message: str
    moved_files: list[SandboxFileRead]
    errors: list[str]  # Partial success — collect errors per file


class CreateFolderRequest(BaseModel):
    relative_path: str  # Path of the new directory (relative to sandbox root)
