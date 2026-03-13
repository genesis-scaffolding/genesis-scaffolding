from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from myproject_core.productivity.models import JournalEntry, JournalType, Project, ProjectTaskLink, Task
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
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

router = APIRouter(prefix="/productivity", tags=["productivity"])


# --- Helper for Dynamic Sorting ---


def apply_sorting(statement, model, sort_by: str, order: str):
    """
    Helper to apply order_by to a statement using getattr to satisfy
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


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, data: ProjectUpdate, session: ProdSessionDep):
    db_project = session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)

    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


# --- TASKS ---


@router.post("/tasks", response_model=TaskRead)
def create_task(data: TaskCreate, session: ProdSessionDep):
    # 1. Create task object (excluding the project_ids helper field)
    task_data = data.model_dump(exclude={"project_ids"})
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


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    session: ProdSessionDep,
    assigned_on: date | None = None,
    project_id: int | None = None,
    include_completed: bool = False,
    sort_by: Literal["assigned_date", "hard_deadline", "title", "status", "created_at"] = "assigned_date",
    order: Literal["asc", "desc"] = "asc",
):
    statement = select(Task).options(selectinload(getattr(Task, "projects")))

    if project_id:
        statement = statement.join(ProjectTaskLink).where(ProjectTaskLink.project_id == project_id)

    if assigned_on:
        statement = statement.where(Task.assigned_date == assigned_on)

    if not include_completed:
        statement = statement.where(Task.status != "completed")

    statement = apply_sorting(statement, Task, sort_by, order)
    return session.exec(statement).all()


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, session: ProdSessionDep):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    # Logic: if status is changed to completed, set completed_at automatically
    if update_data.get("status") == "completed" and db_task.status != "completed":
        db_task.completed_at = datetime.now(timezone.utc)

    for key, value in update_data.items():
        setattr(db_task, key, value)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


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
    ref_date: date | None = None,
    sort_by: Literal["reference_date", "created_at", "updated_at"] = "reference_date",
    order: Literal["asc", "desc"] = "desc",  # Journals default to newest first
):
    statement = select(JournalEntry)
    if entry_type:
        statement = statement.where(JournalEntry.entry_type == entry_type)
    if ref_date:
        statement = statement.where(JournalEntry.reference_date == ref_date)

    statement = apply_sorting(statement, JournalEntry, sort_by, order)
    return session.exec(statement).all()


@router.patch("/journals/{journal_id}", response_model=JournalEntryRead)
def update_journal(journal_id: int, data: JournalEntryUpdate, session: ProdSessionDep):
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)

    db_entry.updated_at = datetime.now(timezone.utc)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


# --- RELATIONSHIP MANAGEMENT ---


@router.post("/tasks/{task_id}/projects/{project_id}")
def link_task_to_project(task_id: int, project_id: int, session: ProdSessionDep):
    """Manually add a relationship."""
    # Check if already exists to avoid unique constraint error
    existing = session.exec(
        select(ProjectTaskLink).where(
            ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id
        )
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
        ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id
    )
    link = session.exec(statement).first()
    if link:
        session.delete(link)
        session.commit()
    return None
