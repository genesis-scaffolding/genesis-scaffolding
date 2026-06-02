"""Service-layer tests for the productivity subsystem.

Regression coverage for the corrupt-task-list bug: the service used to
``setattr`` raw strings onto enum-typed fields, allowing the LLM to write
out-of-enum values (for example ``status='deleted'``) to the database. The
service now validates enum-typed fields up front and raises ``ValueError``
on bad data so the caller's transaction is not half-applied.
"""

import tempfile
from pathlib import Path

import pytest
from genesis_core.productivity import service as prod_service
from genesis_core.productivity.db import _user_engines
from genesis_core.productivity.models import (
    Project,
    Status,
    Task,
    productivity_metadata,
)
from sqlmodel import Session, create_engine


@pytest.fixture
def user_db_url():
    """Yield a fresh SQLite file URL per test, then clean up the engine cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"sqlite:///{Path(tmpdir) / 'user.db'}"
        yield url
        # Drop the engine from the global cache so the next test gets a fresh DB
        _user_engines.pop(url, None)


@pytest.fixture
def user_engine(user_db_url):
    engine = create_engine(
        user_db_url,
        connect_args={"check_same_thread": False},
    )
    productivity_metadata.create_all(engine)
    return engine


def _get_session(engine):
    return Session(engine)


def _create_task(engine, status: str = "todo") -> int:
    task_id: int | None = None
    with _get_session(engine) as session:
        task = prod_service.create_task(session, {"title": "T", "status": status})
        task_id = task.id
    assert task_id is not None
    return task_id


def _create_project(engine) -> int:
    project_id: int | None = None
    with _get_session(engine) as session:
        project = prod_service.create_project(session, {"name": "P"})
        project_id = project.id
    assert project_id is not None
    return project_id


class TestServiceEnumGuard:
    """The service layer must reject invalid enum values before setattr."""

    def test_update_task_rejects_invalid_status(self, user_engine):
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match="Invalid value 'deleted'"):
                prod_service.update_task(session, task_id, {"status": "deleted"})

        # Confirm the row was not mutated
        with _get_session(user_engine) as session:
            task = session.get(Task, task_id)
            assert task is not None
            assert task.status == "todo"

    def test_bulk_update_tasks_rejects_invalid_status_before_writing(self, user_engine):
        """bulk_update_tasks must validate before mutating any row."""
        # Seed two tasks
        task_id_a = _create_task(user_engine)
        task_id_b = _create_task(user_engine)

        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match="Invalid value 'archived'"):
                prod_service.bulk_update_tasks(
                    session,
                    task_ids=[task_id_a, task_id_b],
                    field_updates={"status": "archived"},
                )

        # Both rows must remain untouched
        with _get_session(user_engine) as session:
            task_a = session.get(Task, task_id_a)
            task_b = session.get(Task, task_id_b)
            assert task_a is not None and task_a.status == "todo"
            assert task_b is not None and task_b.status == "todo"

    def test_update_project_rejects_invalid_status(self, user_engine):
        project_id = _create_project(user_engine)
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match="Invalid value 'archived'"):
                prod_service.update_project(session, project_id, {"status": "archived"})

        with _get_session(user_engine) as session:
            project = session.get(Project, project_id)
            assert project is not None
            assert project.status == "todo"

    def test_update_task_accepts_every_valid_status(self, user_engine):
        """No false positives: every Status value must be accepted."""
        for value in [s.value for s in Status]:
            task_id = _create_task(user_engine)
            with _get_session(user_engine) as session:
                updated = prod_service.update_task(session, task_id, {"status": value})
            assert updated is not None
            assert updated.status == value

    def test_update_task_allows_non_enum_field_changes(self, user_engine):
        """The enum guard must not block plain string/date field updates."""
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            updated = prod_service.update_task(
                session,
                task_id,
                {"title": "Renamed", "description": "new body"},
            )
        assert updated is not None
        assert updated.title == "Renamed"
        assert updated.description == "new body"

    def test_update_task_ignores_unknown_fields_silently(self, user_engine):
        """The enum guard only validates known fields; unknown fields pass through.

        This matches the existing setattr behavior where unknown fields are
        silently dropped (``hasattr(db_task, key)`` check). The guard must
        not regress this behavior.
        """
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            # No exception expected; the unknown field is ignored.
            updated = prod_service.update_task(
                session,
                task_id,
                {"title": "Renamed", "not_a_field": "ignored"},
            )
        assert updated is not None
        assert updated.title == "Renamed"
