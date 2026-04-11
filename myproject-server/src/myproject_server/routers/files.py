import mimetypes
import os
import shutil
from base64 import urlsafe_b64decode, urlsafe_b64encode
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ..dependencies import get_current_active_user, get_user_workdir
from ..models.user import User
from ..schemas.file_record import (
    CreateFolderRequest,
    FileMoveRequest,
    FileMoveResponse,
    FileUploadResponse,
    SandboxFileRead,
)

router = APIRouter(prefix="/files", tags=["files"])


def _encode_file_id(relative_path: str) -> str:
    """Encode a relative path to a URL-safe base64 string."""
    return urlsafe_b64encode(relative_path.encode()).rstrip(b"=").decode()


def _decode_file_id(encoded: str) -> str:
    """Decode a URL-safe base64 string back to a relative path."""
    padded = encoded + "=" * (4 - (len(encoded) % 4 or 4))
    return urlsafe_b64decode(padded.encode()).decode()


def _get_sandbox_filesystem(user_workdir: Path):
    """Create a sandbox filesystem instance for the given user workdir."""
    from myproject_core.sandbox_filesystem import LocalSandboxFilesystem

    return LocalSandboxFilesystem(user_workdir)


def _file_info_to_read(file_info) -> SandboxFileRead:
    """Convert a SandboxFileInfo dataclass to a SandboxFileRead Pydantic model."""
    return SandboxFileRead(
        relative_path=file_info.relative_path,
        name=file_info.name,
        is_dir=file_info.is_dir,
        size=file_info.size,
        mime_type=file_info.mime_type,
        mtime=file_info.mtime,
        created_at=file_info.created_at.isoformat() if file_info.created_at else None,
    )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
    subfolder: str = ".",
):
    """Upload a file to subfolder/filename.ext

    The subfolder exists underneath user workdir declared in user_workdir.
    So, the real path on disk would be user_workdir/subfolder/filename.ext
    """
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is missing")

    # Resolve and validate sandbox boundary
    logical_folder = Path(subfolder)
    target_dir = (user_workdir / logical_folder).resolve()

    if not str(target_dir).startswith(str(user_workdir.resolve())):
        raise HTTPException(status_code=403, detail="Traversal attempt detected")

    target_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = os.path.basename(file.filename)
    dest_path = target_dir / safe_filename

    # Write file to disk
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Calculate relative path for response
    relative_path = str(dest_path.relative_to(user_workdir))
    stats = dest_path.stat()

    from myproject_core.schemas import SandboxFileInfo

    file_info = SandboxFileInfo(
        relative_path=relative_path,
        name=dest_path.name,
        is_dir=False,
        size=stats.st_size,
        mime_type=file.content_type or mimetypes.guess_type(dest_path.name)[0] or "application/octet-stream",
        mtime=stats.st_mtime,
    )

    return FileUploadResponse(message="File uploaded successfully", file=_file_info_to_read(file_info))


@router.get("/", response_model=list[FileUploadResponse])
async def list_files(
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
    folder: str = ".",
):
    """List all files in a folder (not including subdirectories)."""
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    fs = _get_sandbox_filesystem(user_workdir)

    try:
        entries = fs.list_directory(folder)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    # Filter to only files (not directories)
    files = [entry for entry in entries if not entry.is_dir]

    return [FileUploadResponse(message="", file=_file_info_to_read(file)) for file in files]


@router.get("/folders", response_model=list[str])
async def list_subfolders(
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
    parent_folder: str = ".",
):
    """List immediate subdirectories under a parent folder."""
    fs = _get_sandbox_filesystem(user_workdir)

    try:
        return fs.get_subdirectories(parent_folder)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/folders", response_model=SandboxFileRead)
async def create_folder(
    request: CreateFolderRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Create a new directory in the sandbox."""
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    if not request.relative_path:
        raise HTTPException(status_code=400, detail="relative_path is required")

    fs = _get_sandbox_filesystem(user_workdir)
    try:
        info = fs.create_directory(request.relative_path)
        return _file_info_to_read(info)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(
    file_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Get file info by encoded relative path."""
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    try:
        relative_path = _decode_file_id(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID encoding") from None

    fs = _get_sandbox_filesystem(user_workdir)

    try:
        file_info = fs.get_file_info(relative_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return FileUploadResponse(message="", file=_file_info_to_read(file_info))


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Get file content as text."""
    try:
        relative_path = _decode_file_id(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID encoding") from None

    fs = _get_sandbox_filesystem(user_workdir)

    try:
        content = fs.read_file(relative_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    try:
        text_content = content.decode("utf-8")
        return {"content": text_content}
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="File is not text-readable") from None


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Download a file."""
    try:
        relative_path = _decode_file_id(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID encoding") from None

    fs = _get_sandbox_filesystem(user_workdir)

    try:
        file_info = fs.get_file_info(relative_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None

    full_path = user_workdir / relative_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path=full_path,
        filename=file_info.name,
        media_type=file_info.mime_type or "application/octet-stream",
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Delete a file."""
    try:
        relative_path = _decode_file_id(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file ID encoding") from None

    fs = _get_sandbox_filesystem(user_workdir)

    try:
        fs.delete_file(relative_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.post("/move", response_model=FileMoveResponse)
async def move_files(
    request: FileMoveRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
):
    """Move multiple files to a destination folder."""
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    if not request.source_paths:
        raise HTTPException(status_code=400, detail="No files specified")

    fs = _get_sandbox_filesystem(user_workdir)

    # Validate destination is within sandbox before touching anything
    try:
        fs.resolve_path(request.destination_folder)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    moved_files: list[SandboxFileRead] = []
    errors: list[str] = []

    for source_path in request.source_paths:
        try:
            # Pre-validate: check it's not a directory
            src_info = fs.get_file_info(source_path)
            if src_info.is_dir:
                errors.append(f"Directory move not supported: {source_path}")
                continue

            filename = Path(source_path).name
            if request.destination_folder == ".":
                dest_path = filename
            else:
                dest_path = f"{request.destination_folder}/{filename}"

            info = fs.move_file(source_path, dest_path)
            moved_files.append(_file_info_to_read(info))
        except FileNotFoundError:
            errors.append(f"File not found: {source_path}")
        except Exception as e:
            errors.append(f"Error moving {source_path}: {str(e)}")

    return FileMoveResponse(
        message=f"Moved {len(moved_files)} file(s)",
        moved_files=moved_files,
        errors=errors,
    )
