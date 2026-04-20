from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from genesis_core.productivity.models import JournalEntry, JournalType, Project, ProjectTaskLink, Task
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlmodel import asc, col, desc, select

from ..dependencies import ProdSessionDep
from ..schemas.productivity import (
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


# --- Helper for Dynamic Sorting ---


def apply_sorting(statement, model, sort_by: str, order: str):
    """Helper to apply order_by to a statement using getattr to satisfy
    linters while accessing SQLModel attributes.
    """
    field = getattr(model, sort_by)
    if order == "desc":
        return statement.order_by(desc(field))
    return statement.order_by(asc(field))


# --- PROJECTS ---


@router.post("/projects", response_model=ProjectRead)
def create_project(data: ProjectCreate, session: ProdSessionDep):
    db_project = Project.model_validate(data)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(
    session: ProdSessionDep,
    sort_by: Literal["name", "deadline", "status", "start_date"] = "name",
    order: Literal["asc", "desc"] = "asc",
):
    statement = select(Project)
    statement = apply_sorting(statement, Project, sort_by, order)
    return session.exec(statement).all()


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, session: ProdSessionDep):
    db_project = session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, data: ProjectUpdate, session: ProdSessionDep):
    db_project = session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True, mode="python")
    for key, value in update_data.items():
        setattr(db_project, key, value)

    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, session: ProdSessionDep):
    db_project = session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    session.delete(db_project)
    session.commit()


# --- TASKS ---


@router.post("/tasks", response_model=TaskRead)
def create_task(data: TaskCreate, session: ProdSessionDep):
    # 1. Create task object (excluding the project_ids helper field)
    task_data = data.model_dump(exclude={"project_ids"}, mode="python")
    db_task = Task.model_validate(task_data)

    # 2. Atomic Link: If project_ids provided, link them now
    if data.project_ids:
        for p_id in data.project_ids:
            project = session.get(Project, p_id)
            if project:
                db_task.projects.append(project)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@router.get("/tasks", response_model=TaskPaginatedResponse)
def list_tasks(
    session: ProdSessionDep,
    assigned_on: date | None = None,
    project_id: int | None = None,
    include_completed: bool = False,
    sort_by: Literal[
        "assigned_date", "hard_deadline", "scheduled_start", "title", "status", "created_at",
    ] = "assigned_date",
    order: Literal["asc", "desc"] = "asc",
    offset: int | None = None,
    limit: int | None = None,
):
    statement = select(Task).options(selectinload(Task.projects))  # type: ignore

    if project_id:
        statement = statement.join(ProjectTaskLink).where(ProjectTaskLink.project_id == project_id)

    if assigned_on:
        statement = statement.where(Task.assigned_date == assigned_on)

    if not include_completed:
        statement = statement.where(Task.status != "completed")

    # Get total count
    count_statement = select(Task)
    if project_id:
        count_statement = count_statement.join(ProjectTaskLink).where(ProjectTaskLink.project_id == project_id)
    if assigned_on:
        count_statement = count_statement.where(Task.assigned_date == assigned_on)
    if not include_completed:
        count_statement = count_statement.where(Task.status != "completed")
    total = len(session.exec(count_statement).all())

    statement = apply_sorting(statement, Task, sort_by, order)

    # Apply pagination only if offset and limit are explicitly provided
    if offset is not None and limit is not None:
        statement = statement.offset(offset).limit(limit)
        actual_offset = offset
        actual_limit = limit
    else:
        # No pagination - return all
        actual_offset = 0
        actual_limit = total

    items = session.exec(statement).all()

    return TaskPaginatedResponse(items=[TaskRead.model_validate(t) for t in items], total=total, offset=actual_offset, limit=actual_limit)


@router.patch("/tasks/bulk", status_code=status.HTTP_200_OK)
def bulk_update_tasks(data: TaskBulkUpdate, session: ProdSessionDep):
    """Perform mass updates on a list of tasks.
    Supports updating fields (status, date) and modifying project links.
    """
    if not data.ids:
        return {"message": "No task IDs provided"}

    # Fetch the tasks that need relationship updates or complex logic
    # We use selectinload to ensure we can modify projects immediately
    statement = (
        select(Task).where(col(Task.id).in_(data.ids)).options(selectinload(Task.projects))  # type: ignore
    )
    tasks = session.exec(statement).all()

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for provided IDs")

    # Extract field updates (excluding relationships)
    field_updates = data.updates.model_dump(exclude_unset=True, mode="python")

    # Apply updates to each task
    for task in tasks:
        # Automatic completion timestamp
        if field_updates.get("status") == "completed" and task.status != "completed":
            task.completed_at = datetime.now(UTC)

        # Reopening a task
        if field_updates.get("status") == "todo" and task.status == "completed":
            task.completed_at = None

        # Apply field updates (this will handle scheduled_start, hard_deadline, etc.)
        for key, value in field_updates.items():
            setattr(task, key, value)

        # Handle Project Sets (Replaces everything)
        if data.set_project_ids is not None:
            new_projects = []
            for p_id in data.set_project_ids:
                proj = session.get(Project, p_id)
                if proj:
                    new_projects.append(proj)
            task.projects = new_projects

        # Handle Additions/Removals (Only if set_project_ids isn't used)
        # Ugly code. To be updated one day when I have time
        else:
            if data.add_project_ids:
                for p_id in data.add_project_ids:
                    if p_id not in [p.id for p in task.projects]:
                        proj = session.get(Project, p_id)
                        if proj:
                            task.projects.append(proj)

            if data.remove_project_ids:
                task.projects = [p for p in task.projects if p.id not in data.remove_project_ids]

        session.add(task)

    session.commit()
    return {"message": f"Successfully updated {len(tasks)} tasks"}


@router.delete("/tasks/bulk", status_code=status.HTTP_200_OK)
def bulk_delete_tasks(task_ids: list[int], session: ProdSessionDep):
    """Delete multiple tasks at once."""
    statement = select(Task).where(col(Task.id).in_(task_ids))
    tasks = session.exec(statement).all()

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for provided IDs")

    for task in tasks:
        session.delete(task)

    session.commit()
    return {"message": f"Successfully deleted {len(tasks)} tasks"}


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: ProdSessionDep):
    # Use selectinload to ensure project_ids are populated
    statement = select(Task).where(Task.id == task_id).options(selectinload(Task.projects))  # type: ignore
    db_task = session.exec(statement).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, session: ProdSessionDep):
    # Fetch with projects loaded so TaskRead can return them
    statement = select(Task).where(Task.id == task_id).options(selectinload(Task.projects))  # type: ignore
    db_task = session.exec(statement).first()

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True, mode="python")

    # Automatic completion timestamp logic
    if update_data.get("status") == "completed" and db_task.status != "completed":
        db_task.completed_at = datetime.now(UTC)
    elif update_data.get("status") is not None and update_data.get("status") != "completed":
        db_task.completed_at = None

    for key, value in update_data.items():
        setattr(db_task, key, value)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: ProdSessionDep):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(db_task)
    session.commit()


# --- JOURNALS ---


@router.post("/journals", response_model=JournalEntryRead)
def create_journal(data: JournalEntryCreate, session: ProdSessionDep):
    db_entry = JournalEntry.model_validate(data)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


@router.get("/journals", response_model=list[JournalEntryRead])
def list_journals(
    session: ProdSessionDep,
    entry_type: JournalType | None = None,
    reference_date: date | None = None,
    sort_by: Literal["reference_date", "created_at", "updated_at"] = "reference_date",
    order: Literal["asc", "desc"] = "desc",  # Journals default to newest first
):
    statement = select(JournalEntry)
    if entry_type:
        statement = statement.where(JournalEntry.entry_type == entry_type)
    if reference_date:
        statement = statement.where(JournalEntry.reference_date == reference_date)

    statement = apply_sorting(statement, JournalEntry, sort_by, order)
    return session.exec(statement).all()


@router.get("/journals/{journal_id}", response_model=JournalEntryRead)
def get_journal(journal_id: int, session: ProdSessionDep):
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return db_entry


@router.patch("/journals/{journal_id}", response_model=JournalEntryRead)
def update_journal(journal_id: int, data: JournalEntryUpdate, session: ProdSessionDep):
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    update_data = data.model_dump(exclude_unset=True, mode="python")
    print(update_data)
    for key, value in update_data.items():
        setattr(db_entry, key, value)

    db_entry.updated_at = datetime.now(UTC)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


@router.delete("/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: int, session: ProdSessionDep):
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    session.delete(db_entry)
    session.commit()


# --- RELATIONSHIP MANAGEMENT ---


@router.post("/tasks/{task_id}/projects/{project_id}")
def link_task_to_project(task_id: int, project_id: int, session: ProdSessionDep):
    """Manually add a relationship."""
    # Check if already exists to avoid unique constraint error
    existing = session.exec(
        select(ProjectTaskLink).where(
            ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id,
        ),
    ).first()

    if not existing:
        link = ProjectTaskLink(task_id=task_id, project_id=project_id)
        session.add(link)
        session.commit()
    return {"status": "linked"}


@router.delete("/tasks/{task_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_task_from_project(task_id: int, project_id: int, session: ProdSessionDep):
    """Removes the relationship between a task and a project."""
    statement = select(ProjectTaskLink).where(
        ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id,
    )
    link = session.exec(statement).first()
    if link:
        session.delete(link)
        session.commit()
