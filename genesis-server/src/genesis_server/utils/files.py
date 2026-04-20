import mimetypes
import time
from pathlib import Path

from sqlmodel import Session, select

from ..models.file_record import FileRecord

# Simple in-memory cache to prevent spamming the disk
# Format: {(user_id, folder_path): last_sync_time}
_last_sync_cache = {}


def sync_folder_shallow(session: Session, user_id: int, user_sandbox_path: Path, folder_path: str = "."):
    """Syncs only the immediate contents of a specific folder.
    This is an optimisation to avoid rglob on entire disk every time we touch files endpoint
    """
    current_time = time.time()
    cache_key = (user_id, folder_path)

    # 1. Rate Limiting: Don't sync the same folder more than once every 3 seconds
    if current_time - _last_sync_cache.get(cache_key, 0) < 3:
        return

    target_dir = (user_sandbox_path / folder_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        return

    # Directory MTime Check:
    # Most filesystems update the directory's mtime when files are added/deleted.
    # This is a very "cheap" way to check if we even need to look at the disk.

    # Perform Shallow Scan
    files_on_disk = {}
    for entry in target_dir.iterdir():
        if entry.is_file():
            # Logical path relative to sandbox root
            rel_path = str(entry.relative_to(user_sandbox_path))
            files_on_disk[rel_path] = entry

    print(files_on_disk)

    # 4. Get current DB state for this folder only
    statement = select(FileRecord).where(FileRecord.user_id == user_id, FileRecord.folder == folder_path)
    db_records = {r.relative_path: r for r in session.exec(statement).all()}

    # 5. Reconcile
    # Add/Update
    for rel_path, path in files_on_disk.items():
        stats = path.stat()
        if rel_path not in db_records:
            new_record = FileRecord(
                filename=path.name,
                # file_path=str(path.relative_to(settings.path.inbox_directory)),
                file_path=str(path.relative_to(user_sandbox_path)),
                relative_path=rel_path,
                folder=folder_path,
                mime_type=mimetypes.guess_type(path)[0] or "application/octet-stream",
                size=stats.st_size,
                user_id=user_id,
            )
            session.add(new_record)
        elif db_records[rel_path].size != stats.st_size:
            # Update size if changed
            db_records[rel_path].size = stats.st_size
            session.add(db_records[rel_path])

    # Remove deleted
    for rel_path, record in db_records.items():
        if rel_path not in files_on_disk:
            session.delete(record)

    session.commit()
    _last_sync_cache[cache_key] = current_time
