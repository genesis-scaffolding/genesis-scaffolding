from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from genesis_core.productivity.models import JournalType
from pydantic import BaseModel

from genesis_server.dependencies import CoreDep
from genesis_server.schemas.productivity import (
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    TaskBulkUpdate,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)


class TaskPaginatedResponse(BaseModel):
    items: list[TaskRead]
    total: int
    offset: int
    limit: int


router = APIRouter(prefix="/productivity", tags=["productivity"])


# --- PROJECTS ---


@router.post("/projects", response_model=ProjectRead)
async def create_project(data: ProjectCreate, core: CoreDep):
    """Create a new project."""
    project = core.productivity_manager.create_project(data.model_dump())
    return project


@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(
    core: CoreDep,
    sort_by: Literal["name", "deadline", "status", "start_date"] = "name",
    order: Literal["asc", "desc"] = "asc",
):
    """List all projects."""
    return core.productivity_manager.list_projects(sort_by=sort_by, order=order)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, core: CoreDep):
    """Get a project by ID."""
    project = core.productivity_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, data: ProjectUpdate, core: CoreDep):
    """Update a project."""
    project = core.productivity_manager.update_project(project_id, data.model_dump(exclude_unset=True, mode="python"))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, core: CoreDep):
    """Delete a project."""
    if not core.productivity_manager.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")


# --- TASKS ---


@router.post("/tasks", response_model=TaskRead)
async def create_task(data: TaskCreate, core: CoreDep):
    """Create a new task."""
    task_data = data.model_dump(exclude={"project_ids"}, mode="python")
    task = core.productivity_manager.create_task(task_data, project_ids=data.project_ids)
    return task


@router.get("/tasks", response_model=TaskPaginatedResponse)
async def list_tasks(
    core: CoreDep,
    assigned_on: datetime | None = None,
    project_id: int | None = None,
    include_completed: bool = False,
    sort_by: Literal[
        "assigned_date", "hard_deadline", "scheduled_start", "title", "status", "created_at",
    ] = "assigned_date",
    order: Literal["asc", "desc"] = "asc",
    offset: int | None = None,
    limit: int | None = None,
):
    """List tasks with optional filtering and pagination."""
    tasks = core.productivity_manager.list_tasks(
        assigned_on=assigned_on,
        project_id=project_id,
        include_completed=include_completed,
        sort_by=sort_by,
        order=order,
    )
    total = len(tasks)

    if offset is not None and limit is not None:
        tasks = tasks[offset:offset + limit]
        actual_offset = offset
        actual_limit = limit
    else:
        actual_offset = 0
        actual_limit = total

    return TaskPaginatedResponse(
        items=[TaskRead.model_validate(t) for t in tasks],
        total=total,
        offset=actual_offset,
        limit=actual_limit,
    )


@router.patch("/tasks/bulk", status_code=status.HTTP_200_OK)
async def bulk_update_tasks(data: TaskBulkUpdate, core: CoreDep):
    """Perform mass updates on a list of tasks."""
    if not data.ids:
        return {"message": "No task IDs provided"}
    updated = core.productivity_manager.bulk_update_tasks(
        task_ids=data.ids,
        field_updates=data.updates.model_dump(exclude_unset=True, mode="python"),
        set_project_ids=data.set_project_ids,
        add_project_ids=data.add_project_ids,
        remove_project_ids=data.remove_project_ids,
    )
    return {"message": f"Successfully updated {updated} tasks"}


@router.delete("/tasks/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete_tasks(task_ids: list[int], core: CoreDep):
    """Delete multiple tasks at once."""
    if not task_ids:
        return {"message": "No task IDs provided"}
    deleted = core.productivity_manager.bulk_delete_tasks(task_ids)
    return {"message": f"Successfully deleted {deleted} tasks"}


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, core: CoreDep):
    """Get a task by ID."""
    task = core.productivity_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, data: TaskUpdate, core: CoreDep):
    """Update a task."""
    task = core.productivity_manager.update_task(task_id, data.model_dump(exclude_unset=True, mode="python"))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, core: CoreDep):
    """Delete a task."""
    if not core.productivity_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


# --- JOURNALS ---


@router.post("/journals", response_model=JournalEntryRead)
async def create_journal(data: JournalEntryCreate, core: CoreDep):
    """Create a new journal entry."""
    entry = core.productivity_manager.create_journal(data.model_dump())
    return entry


@router.get("/journals", response_model=list[JournalEntryRead])
async def list_journals(
    core: CoreDep,
    entry_type: str | None = None,
    reference_date: datetime | None = None,
    project_id: int | None = None,
    sort_by: Literal["reference_date", "created_at", "updated_at"] = "reference_date",
    order: Literal["asc", "desc"] = "desc",
):
    """List journal entries."""
    journal_type = JournalType(entry_type) if entry_type else None
    journals = core.productivity_manager.list_journals(
        entry_type=journal_type,
        reference_date=reference_date,
        sort_by=sort_by,
        order=order,
    )
    return journals


@router.get("/journals/{journal_id}", response_model=JournalEntryRead)
async def get_journal(journal_id: int, core: CoreDep):
    """Get a journal entry by ID."""
    entry = core.productivity_manager.get_journal(journal_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.patch("/journals/{journal_id}", response_model=JournalEntryRead)
async def update_journal(journal_id: int, data: JournalEntryUpdate, core: CoreDep):
    """Update a journal entry."""
    entry = core.productivity_manager.update_journal(journal_id, data.model_dump(exclude_unset=True, mode="python"))
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.delete("/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal(journal_id: int, core: CoreDep):
    """Delete a journal entry."""
    if not core.productivity_manager.delete_journal(journal_id):
        raise HTTPException(status_code=404, detail="Journal entry not found")


# --- RELATIONSHIP MANAGEMENT ---


@router.post("/tasks/{task_id}/projects/{project_id}")
async def link_task_to_project(task_id: int, project_id: int, core: CoreDep):
    """Add a project to a task."""
    task = core.productivity_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = core.productivity_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Add project to task's project list
    task.projects.append(project)
    core.productivity_manager.update_task(task_id, {"projects": task.projects})
    return {"status": "linked"}


@router.delete("/tasks/{task_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_task_from_project(task_id: int, project_id: int, core: CoreDep):
    """Remove a project from a task."""
    task = core.productivity_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.projects = [p for p in task.projects if p.id != project_id]
    core.productivity_manager.update_task(task_id, {"projects": task.projects})
