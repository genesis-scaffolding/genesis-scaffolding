from datetime import date, datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import selectinload
from sqlmodel import Session, asc, col, desc, select

from .models import JournalEntry, JournalType, Project, ProjectTaskLink, Task

# --- Helper ---


def _apply_sorting(statement, model, sort_by: str, order: str):
    """Helper to apply order_by dynamically."""
    if not hasattr(model, sort_by):
        return statement  # Fallback if invalid sort field is provided

    field = getattr(model, sort_by)
    if order == "desc":
        return statement.order_by(desc(field))
    return statement.order_by(asc(field))


# --- PROJECTS ---


def get_project(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def list_projects(
    session: Session,
    sort_by: Literal["name", "deadline", "status", "start_date"] = "name",
    order: Literal["asc", "desc"] = "asc",
) -> list[Project]:
    statement = select(Project)
    statement = _apply_sorting(statement, Project, sort_by, order)
    return session.exec(statement).all()


def create_project(session: Session, data: dict[str, Any]) -> Project:
    db_project = Project.model_validate(data)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


def update_project(session: Session, project_id: int, data: dict[str, Any]) -> Project | None:
    db_project = session.get(Project, project_id)
    if not db_project:
        return None

    for key, value in data.items():
        if hasattr(db_project, key):
            setattr(db_project, key, value)

    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


def delete_project(session: Session, project_id: int) -> bool:
    db_project = session.get(Project, project_id)
    if not db_project:
        return False
    session.delete(db_project)
    session.commit()
    return True


# --- TASKS ---


def get_task(session: Session, task_id: int) -> Task | None:
    statement = select(Task).where(Task.id == task_id).options(selectinload(getattr(Task, "projects")))
    return session.exec(statement).first()


def list_tasks(
    session: Session,
    assigned_on: date | None = None,
    project_id: int | None = None,
    include_completed: bool = False,
    sort_by: Literal[
        "assigned_date", "hard_deadline", "scheduled_start", "title", "status", "created_at"
    ] = "assigned_date",
    order: Literal["asc", "desc"] = "asc",
) -> list[Task]:
    statement = select(Task).options(selectinload(getattr(Task, "projects")))

    if project_id:
        statement = statement.join(ProjectTaskLink).where(ProjectTaskLink.project_id == project_id)

    if assigned_on:
        statement = statement.where(Task.assigned_date == assigned_on)

    if not include_completed:
        statement = statement.where(Task.status != "completed")

    statement = _apply_sorting(statement, Task, sort_by, order)
    return session.exec(statement).all()


def create_task(session: Session, data: dict[str, Any], project_ids: list[int] | None = None) -> Task:
    db_task = Task.model_validate(data)

    if project_ids:
        for p_id in project_ids:
            project = session.get(Project, p_id)
            if project:
                db_task.projects.append(project)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def update_task(session: Session, task_id: int, data: dict[str, Any]) -> Task | None:
    statement = select(Task).where(Task.id == task_id).options(selectinload(getattr(Task, "projects")))
    db_task = session.exec(statement).first()

    if not db_task:
        return None

    # Handle completion timestamp logic automatically
    if data.get("status") == "completed" and db_task.status != "completed":
        db_task.completed_at = datetime.now(timezone.utc)
    elif data.get("status") is not None and data.get("status") != "completed":
        db_task.completed_at = None

    for key, value in data.items():
        if hasattr(db_task, key):
            setattr(db_task, key, value)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def delete_task(session: Session, task_id: int) -> bool:
    db_task = session.get(Task, task_id)
    if not db_task:
        return False
    session.delete(db_task)
    session.commit()
    return True


def bulk_update_tasks(
    session: Session,
    task_ids: list[int],
    field_updates: dict[str, Any],
    set_project_ids: list[int] | None = None,
    add_project_ids: list[int] | None = None,
    remove_project_ids: list[int] | None = None,
) -> int:
    """Updates multiple tasks, returns the number of tasks successfully updated."""
    if not task_ids:
        return 0

    statement = (
        select(Task).where(col(Task.id).in_(task_ids)).options(selectinload(getattr(Task, "projects")))
    )
    tasks = session.exec(statement).all()

    for task in tasks:
        # Automatic completion timestamp
        if field_updates.get("status") == "completed" and task.status != "completed":
            task.completed_at = datetime.now(timezone.utc)
        if field_updates.get("status") == "todo" and task.status == "completed":
            task.completed_at = None

        # Apply basic fields
        for key, value in field_updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Handle Project Sets (Replaces everything)
        if set_project_ids is not None:
            new_projects = []
            for p_id in set_project_ids:
                proj = session.get(Project, p_id)
                if proj:
                    new_projects.append(proj)
            task.projects = new_projects
        else:
            # Handle Additions/Removals
            if add_project_ids:
                existing_pids = {p.id for p in task.projects}
                for p_id in add_project_ids:
                    if p_id not in existing_pids:
                        proj = session.get(Project, p_id)
                        if proj:
                            task.projects.append(proj)

            if remove_project_ids:
                remove_set = set(remove_project_ids)
                task.projects = [p for p in task.projects if p.id not in remove_set]

        session.add(task)

    session.commit()
    return len(tasks)


def bulk_delete_tasks(session: Session, task_ids: list[int]) -> int:
    if not task_ids:
        return 0
    statement = select(Task).where(col(Task.id).in_(task_ids))
    tasks = session.exec(statement).all()

    for task in tasks:
        session.delete(task)

    session.commit()
    return len(tasks)


# --- JOURNALS ---


def get_journal(session: Session, journal_id: int) -> JournalEntry | None:
    return session.get(JournalEntry, journal_id)


def list_journals(
    session: Session,
    entry_type: JournalType | None = None,
    reference_date: date | None = None,
    sort_by: Literal["reference_date", "created_at", "updated_at"] = "reference_date",
    order: Literal["asc", "desc"] = "desc",
) -> list[JournalEntry]:
    statement = select(JournalEntry)
    if entry_type:
        statement = statement.where(JournalEntry.entry_type == entry_type)
    if reference_date:
        statement = statement.where(JournalEntry.reference_date == reference_date)

    statement = _apply_sorting(statement, JournalEntry, sort_by, order)
    return session.exec(statement).all()


def create_journal(session: Session, data: dict[str, Any]) -> JournalEntry:
    db_entry = JournalEntry.model_validate(data)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


def update_journal(session: Session, journal_id: int, data: dict[str, Any]) -> JournalEntry | None:
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        return None

    for key, value in data.items():
        if hasattr(db_entry, key):
            setattr(db_entry, key, value)

    db_entry.updated_at = datetime.now(timezone.utc)
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry


def delete_journal(session: Session, journal_id: int) -> bool:
    db_entry = session.get(JournalEntry, journal_id)
    if not db_entry:
        return False
    session.delete(db_entry)
    session.commit()
    return True


# --- RELATIONSHIPS (Convenience) ---


def link_task_to_project(session: Session, task_id: int, project_id: int) -> bool:
    existing = session.exec(
        select(ProjectTaskLink).where(
            ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id
        )
    ).first()

    if not existing:
        link = ProjectTaskLink(task_id=task_id, project_id=project_id)
        session.add(link)
        session.commit()
        return True
    return False


def unlink_task_from_project(session: Session, task_id: int, project_id: int) -> bool:
    statement = select(ProjectTaskLink).where(
        ProjectTaskLink.task_id == task_id, ProjectTaskLink.project_id == project_id
    )
    link = session.exec(statement).first()
    if link:
        session.delete(link)
        session.commit()
        return True
    return False
