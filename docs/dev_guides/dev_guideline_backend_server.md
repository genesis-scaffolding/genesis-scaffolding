# Design Guideline for Updating FastAPI Backend

Imaging you are adding a feature like `news` to the system. You must do the following:
1.  Define the **storage** logic and API endpoints in the backend to store and serve the data (e.g., news).
2.  Implement the **server actions and UI** in the frontend to consume the data.

This guide outlines how to add new database entities and endpoints to the FastAPI backend. 

## Quick overview of the backend

The backend implementation is spread across two Python monorepo.

The `myproject-server` monorepo, which contains the `myproject_server` package handles the FastAPI, user management, server's databases. Internally, it uses the code from the `myproject-core` monorepo.

The `myproject-core` monorepo contains the `myproject_core` package, which provides the logic for the following main features:
- `myproject_core.configs`: handling configurations, including reading from dotenv files and merging configs with YAML files. 
- `myproject_core.agent_registry`: provide a registry for known LLM agents. These agents can be used directly by user in chat sessions, or by workflows
- `myproject_core.agent`: provide the logic for triggering an LLM agent to start processing a user input. Internally, it would call LLM provider, execute tool calls, and update internal state of the agent. 
- `myproject_core.workflow_registry`: provide a registry for known workflows, which could use LLM agents to carry out user-defined processes. These processes are written in YAML. 
- `myproject_core.workflow_engine`: provide the logic for actually executing a workflow.

Noted that the `myproject_core` does not have the concept of multi-user. Therefore, it can be used in a single-user environment, such as a CLI tool. The `myproject_server` brings the concept of multi-user to the table.

---

## 1. Categorize the Entity
Before coding, determine the ownership model to decide where data is stored:

*   **System-wide Entity**: Relevant to the entire system or every user (e.g., system status snapshots). Stored in the **Main Database**.
*   **User-owned, System-used**: Owned by a user but required by the system for operations (e.g., custom LLM provider credentials). Stored in the **Main Database**.
*   **Private Entity**: Personal user data (e.g., todo lists, journals). Stored in the **User’s Private Database**.

---

## 2. Create Models and Schemas
### Database Models
Define models in `myproject_server.models` using `sqlmodel`. These define the database table structure.

```python
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from .user import User

class FileRecordBase(SQLModel):
    filename: str = Field(index=True)
    file_path: str
    relative_path: str = Field(index=True)
    folder: str = Field(default=".", index=True)
    mime_type: str | None = None
    size: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FileRecord(FileRecordBase, table=True):
    __table_args__ = (UniqueConstraint("user_id", "relative_path", name="unique_user_file_path"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    user: "User" = Relationship()
```

### Pydantic Schemas
Define schemas in `myproject_server.schemas` to control API input/output. These are often subsets or extensions of your models.

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class FileRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    relative_path: str
    folder: str
    mime_type: str | None
    size: int | None
    created_at: datetime

class FileUploadResponse(BaseModel):
    message: str
    file: FileRecordRead
```

---

## 3. Utilize Dependency Injections
Use `myproject_server.dependencies` to access context at runtime:

*   **`get_session()`**: Provides an SQL database session for the main DB.
*   **`get_current_active_user()`**: Returns the authenticated `User` object.
*   **`get_user_workdir()`**: Returns the `Path` to the user's isolated sandbox.
*   **`get_user_config()`**: Returns a user-specific `Config` object (overrides system defaults).
*   **`get_agent_registry()` / `get_workflow_registry()`**: Access blueprints for AI agents or workflow manifests.
*   **`get_workflow_engine()`**: Returns a pre-configured engine to execute workflows in the user's sandbox.

---

## 4. Write FastAPI Routers
Create a new module in `myproject_server.routers`. Adhere to **RESTful** principles:

*   **Collections (`/files`)**: 
    *   `GET`: List items.
    *   `POST`: Create a new item.
*   **Individual Resources (`/files/{id}`)**:
    *   `GET`: Fetch details.
    *   `PATCH`: Update.
    *   `DELETE`: Remove.

Avoid procedural paths like `/submit-data`; use standard HTTP verbs against resource paths instead.

---

## 5. Integration
1.  Import your router into `myproject_server.main`.
2.  Include it in the main FastAPI app: `app.include_router(your_router)`.
3.  Verify the implementation via SwaggerUI at `http://localhost:8000/docs`.

---

## Code Sample: File Router
Below is an example implementation for the `FileRecord` entity.

```python
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
    physical_rel_path = dest_path.relative_to(user_path)
    user_rel_path = dest_path.relative_to(user_path)

    # 4. UPSERT LOGIC
    statement = select(FileRecord).where(
        FileRecord.user_id == user.id, FileRecord.relative_path == str(user_rel_path)
    )
    existing_record = session.exec(statement).first()

    if existing_record:
        existing_record.size = dest_path.stat().st_size
        existing_record.mime_type = file.content_type
        session.add(existing_record)
        db_record = existing_record
        message = "File updated successfully"
    else:
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
    statement = select(FileRecord).where(FileRecord.id == file_id, FileRecord.user_id == user.id)
    file_record = session.exec(statement).first()

    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    full_path = user_path / file_record.file_path
    if full_path.exists():
        try:
            full_path.unlink()
            parent_dir = full_path.parent
            user_root = user_path.resolve()
            if parent_dir != user_root and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
        except Exception as e:
            print(f"Cleanup error: {e}")

    session.delete(file_record)
    session.commit()
    return None


@router.get("/folders", response_model=list[str])
async def list_subfolders(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    parent_folder: str = ".",
):
    statement = (
        select(FileRecord.folder)
        .where(FileRecord.user_id == user.id, FileRecord.folder != ".")
        .distinct()
    )
    all_folders = session.exec(statement).all()

    children = set()
    parent_path = Path(parent_folder)
    for f in all_folders:
        f_path = Path(f)
        if parent_folder == "." or f_path.is_relative_to(parent_path):
            relative = f_path.relative_to(parent_path)
            if relative.parts:
                children.add(relative.parts[0])

    return sorted(list(children))
```
