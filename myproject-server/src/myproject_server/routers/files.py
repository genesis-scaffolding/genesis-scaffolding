import os
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..database import get_session
from ..dependencies import get_current_active_user, get_user_inbox_path
from ..models.file_record import FileRecord
from ..models.user import User
from ..schemas.file_record import FileRecordRead, FileUploadResponse
from ..utils.files import sync_folder_shallow

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    user: Annotated[User, Depends(get_current_active_user)],
    user_path: Annotated[Path, Depends(get_user_inbox_path)],
    session: Annotated[Session, Depends(get_session)],
    subfolder: str = ".",
):
    """
    Upload a file to subfolder/filename.ext
    The subfolder exist underneath user inbox declared in user_path
    So, the real path on disk would be user_path/subfolder/filename.ext
    """
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is missing")

    # 1. Resolve and Validate Sandbox Boundary
    # We use subfolder as a logical path
    logical_folder = Path(subfolder)
    target_dir = (user_path / logical_folder).resolve()

    if not str(target_dir).startswith(str(user_path.resolve())):
        raise HTTPException(status_code=403, detail="Traversal attempt detected")

    target_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = os.path.basename(file.filename)
    dest_path = target_dir / safe_filename

    # 2. Disk IO
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Calculate paths for DB
    # Turn everything relative to avoid leaking absolute path of server
    # Relative to the global inbox for physical access
    physical_rel_path = dest_path.relative_to(user_path)
    # Relative to user's root for their UI/filtering
    user_rel_path = dest_path.relative_to(user_path)

    # 4. UPSERT LOGIC: Check if file record already exists
    statement = select(FileRecord).where(
        FileRecord.user_id == user.id, FileRecord.relative_path == str(user_rel_path)
    )
    existing_record = session.exec(statement).first()

    if existing_record:
        # Update existing record
        existing_record.size = dest_path.stat().st_size
        existing_record.mime_type = file.content_type
        # Optional: update a modified_at timestamp if you add one to your model
        session.add(existing_record)
        db_record = existing_record
        message = "File updated successfully"
    else:
        # Create new record
        db_record = FileRecord(
            filename=safe_filename,
            file_path=str(physical_rel_path),
            relative_path=str(user_rel_path),
            folder=str(user_rel_path.parent),
            mime_type=file.content_type,
            size=dest_path.stat().st_size,
            user_id=user.id,
        )
        session.add(db_record)
        message = "File uploaded successfully"

    session.commit()
    session.refresh(db_record)

    return {"message": message, "file": db_record}


@router.get("/", response_model=list[FileRecordRead])
async def list_files(
    user: Annotated[User, Depends(get_current_active_user)],
    user_path: Annotated[Path, Depends(get_user_inbox_path)],
    session: Annotated[Session, Depends(get_session)],
    folder: str = ".",
):
    if not user.id:
        raise HTTPException(status_code=403, detail="User not found")

    sync_folder_shallow(session, user.id, user_path, folder)

    statement = select(FileRecord).where(FileRecord.user_id == user.id)

    if folder:
        # DB-level filtering: No Python loops, minimal CPU usage
        statement = statement.where(FileRecord.folder == str(Path(folder)))

    results = session.exec(statement).all()
    return results


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    user_path: Annotated[Path, Depends(get_user_inbox_path)],
):
    statement = select(FileRecord).where(FileRecord.id == file_id, FileRecord.user_id == user.id)
    file_record = session.exec(statement).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    full_path = user_path / file_record.file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(path=full_path, filename=file_record.filename, media_type=file_record.mime_type)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    user_path: Annotated[Path, Depends(get_user_inbox_path)],
):
    # 1. Database lookup with ownership check
    statement = select(FileRecord).where(FileRecord.id == file_id, FileRecord.user_id == user.id)
    file_record = session.exec(statement).first()

    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # 2. Physical Cleanup
    full_path = user_path / file_record.file_path
    if full_path.exists():
        try:
            full_path.unlink()

            # Optional: Clean up empty parent directories in the sandbox
            # only if they are not the user's root directory.
            parent_dir = full_path.parent
            user_root = user_path.resolve()

            if parent_dir != user_root and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
        except Exception as e:
            # Log error but proceed with DB cleanup to avoid state desync
            print(f"Cleanup error: {e}")

    # 3. Database Cleanup
    session.delete(file_record)
    session.commit()

    return None


@router.get("/folders", response_model=list[str])
async def list_subfolders(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    parent_folder: str = ".",
):
    # Select unique folders that belong to this user
    # We look for folders that start with the parent_folder path
    statement = (
        select(FileRecord.folder)
        .where(
            FileRecord.user_id == user.id,
            FileRecord.folder != ".",  # usually we want to exclude the root from the 'subfolder' search
        )
        .distinct()
    )

    all_folders = session.exec(statement).all()

    # Logic to return only the immediate children of parent_folder
    # e.g., if parent is "docs", return "docs/work", but not "docs/work/2026"
    children = set()
    parent_path = Path(parent_folder)

    for f in all_folders:
        f_path = Path(f)
        if parent_folder == "." or f_path.is_relative_to(parent_path):
            # Get the part immediately after the parent
            relative = f_path.relative_to(parent_path)
            if relative.parts:
                children.add(relative.parts[0])

    return sorted(list(children))
