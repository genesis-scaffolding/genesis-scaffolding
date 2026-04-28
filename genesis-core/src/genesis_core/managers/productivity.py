"""
Productivity subsystem manager for genesis_core.

Wraps the productivity database (user_private.db) and provides CRUD operations
for Projects, Tasks, and JournalEntries.
"""

from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..configs import Config
from ..productivity.db import get_user_engine
from ..productivity.models import JournalEntry, JournalType, Project, ProjectTaskLink, Task


class ProductivityManager:
    """Manager for productivity subsystem (Projects, Tasks, Journals)."""

    def __init__(self, config: Config):
        self.config = config
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = get_user_engine(self.config)
        return self._engine

    def _session(self):
        from sqlmodel import Session as SQLSession
        return SQLSession(self._get_engine())

    # --- PROJECTS ---

    def get_project(self, project_id: int) -> Project | None:
        with self._session() as session:
            return session.get(Project, project_id)

    def list_projects(
        self,
        sort_by: Literal["name", "deadline", "status", "start_date"] = "name",
        order: Literal["asc", "desc"] = "asc",
    ) -> list[Project]:
        with self._session() as session:
            statement = select(Project)
            statement = self._apply_sorting(statement, Project, sort_by, order)
            return list(session.exec(statement).all())

    def create_project(self, data: dict[str, Any]) -> Project:
        with self._session() as session:
            db_project = Project.model_validate(data)
            session.add(db_project)
            session.commit()
            session.refresh(db_project)
            return db_project

    def update_project(self, project_id: int, data: dict[str, Any]) -> Project | None:
        with self._session() as session:
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

    def delete_project(self, project_id: int) -> bool:
        with self._session() as session:
            db_project = session.get(Project, project_id)
            if not db_project:
                return False
            session.delete(db_project)
            session.commit()
            return True

    # --- TASKS ---

    def get_task(self, task_id: int) -> Task | None:
        with self._session() as session:
            statement = select(Task).where(Task.id == task_id)
            return session.exec(statement).first()

    def list_tasks(
        self,
        assigned_on: date | None = None,
        project_id: int | None = None,
        include_completed: bool = False,
        sort_by: Literal[
            "assigned_date", "hard_deadline", "scheduled_start", "title", "status", "created_at",
        ] = "assigned_date",
        order: Literal["asc", "desc"] = "asc",
    ) -> list[Task]:
        with self._session() as session:
            # selectinload is the correct SQLAlchemy eager-load pattern; the string key
            # form is valid at runtime but pyright's SQLAlchemy stubs can't resolve it
            statement = select(Task).options(selectinload(Task.projects))  # type: ignore[reportArgumentType]
            if project_id:
                statement = statement.join(ProjectTaskLink).where(ProjectTaskLink.project_id == project_id)
            if assigned_on:
                statement = statement.where(Task.assigned_date == assigned_on)
            if not include_completed:
                statement = statement.where(Task.status != "completed")
            statement = self._apply_sorting(statement, Task, sort_by, order)
            return list(session.exec(statement).all())

    def create_task(self, data: dict[str, Any], project_ids: list[int] | None = None) -> Task:
        with self._session() as session:
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

    def update_task(self, task_id: int, data: dict[str, Any]) -> Task | None:
        with self._session() as session:
            db_task = session.get(Task, task_id)
            if not db_task:
                return None
            if data.get("status") == "completed" and db_task.status != "completed":
                db_task.completed_at = datetime.now(UTC)
            elif data.get("status") is not None and data.get("status") != "completed":
                db_task.completed_at = None
            for key, value in data.items():
                if hasattr(db_task, key):
                    setattr(db_task, key, value)
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            return db_task

    def delete_task(self, task_id: int) -> bool:
        with self._session() as session:
            db_task = session.get(Task, task_id)
            if not db_task:
                return False
            session.delete(db_task)
            session.commit()
            return True

    def bulk_update_tasks(
        self,
        task_ids: list[int],
        field_updates: dict[str, Any],
        set_project_ids: list[int] | None = None,
        add_project_ids: list[int] | None = None,
        remove_project_ids: list[int] | None = None,
    ) -> int:
        if not task_ids:
            return 0
        with self._session() as session:
            from sqlmodel import col
            statement = select(Task).where(col(Task.id).in_(task_ids))
            tasks = session.exec(statement).all()
            for task in tasks:
                if field_updates.get("status") == "completed" and task.status != "completed":
                    task.completed_at = datetime.now(UTC)
                for key, value in field_updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                if set_project_ids is not None:
                    new_projects = []
                    for p_id in set_project_ids:
                        proj = session.get(Project, p_id)
                        if proj:
                            new_projects.append(proj)
                    task.projects = new_projects
                else:
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

    def bulk_delete_tasks(self, task_ids: list[int]) -> int:
        if not task_ids:
            return 0
        with self._session() as session:
            from sqlmodel import col
            statement = select(Task).where(col(Task.id).in_(task_ids))
            tasks = session.exec(statement).all()
            for task in tasks:
                session.delete(task)
            session.commit()
            return len(tasks)

    # --- JOURNALS ---

    def get_journal(self, journal_id: int) -> JournalEntry | None:
        with self._session() as session:
            return session.get(JournalEntry, journal_id)

    def list_journals(
        self,
        entry_type: JournalType | None = None,
        reference_date: date | None = None,
        sort_by: Literal["reference_date", "created_at", "updated_at"] = "reference_date",
        order: Literal["asc", "desc"] = "desc",
    ) -> list[JournalEntry]:
        with self._session() as session:
            statement = select(JournalEntry)
            if entry_type:
                statement = statement.where(JournalEntry.entry_type == entry_type)
            if reference_date:
                statement = statement.where(JournalEntry.reference_date == reference_date)
            statement = self._apply_sorting(statement, JournalEntry, sort_by, order)
            return list(session.exec(statement).all())

    def create_journal(self, data: dict[str, Any]) -> JournalEntry:
        with self._session() as session:
            db_entry = JournalEntry.model_validate(data)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def update_journal(self, journal_id: int, data: dict[str, Any]) -> JournalEntry | None:
        with self._session() as session:
            db_entry = session.get(JournalEntry, journal_id)
            if not db_entry:
                return None
            for key, value in data.items():
                if hasattr(db_entry, key):
                    setattr(db_entry, key, value)
            db_entry.updated_at = datetime.now(UTC)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def delete_journal(self, journal_id: int) -> bool:
        with self._session() as session:
            db_entry = session.get(JournalEntry, journal_id)
            if not db_entry:
                return False
            session.delete(db_entry)
            session.commit()
            return True

    # --- HELPERS ---

    @staticmethod
    def _apply_sorting(statement, model, sort_by: str, order: str):
        if not hasattr(model, sort_by):
            return statement
        field = getattr(model, sort_by)
        if order == "desc":
            return statement.order_by(field.desc())
        return statement.order_by(field.asc())
