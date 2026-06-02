"""Service-layer tests for the productivity subsystem.

Regression coverage for the corrupt-task-list bug: the service used to
``setattr`` raw strings onto enum-typed fields, allowing the LLM to write
out-of-enum values (for example ``status='deleted'``) to the database. The
service now validates enum-typed fields up front and raises ``ValueError``
on bad data so the caller's transaction is not half-applied.
"""

import tempfile
from datetime import date
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
from sqlmodel import Session, create_engine, select


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


# --- Foreign-key existence and blank-string guards (B1-B5) ---


class TestForeignKeyGuards:
    """B1-B4: the service must reject non-existent project references."""

    def test_create_task_rejects_missing_project_id(self, user_engine):
        """B3: a non-existent ID in project_ids must raise ValueError."""
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"Project\(s\) not found"):
                prod_service.create_task(
                    session,
                    {"title": "Linked to ghost", "status": "todo"},
                    project_ids=[99999],
                )

        # Confirm no row was written
        with _get_session(user_engine) as session:
            assert list(session.exec(select(Task)).all()) == []

    def test_create_task_with_mixed_valid_and_invalid_project_ids_rejects(self, user_engine):
        """B3 (multi-ID): if ANY ID is missing, the whole call must be rejected.

        A partial success (some links created, others silently skipped) is
        exactly the silent orphan-link bug this guard exists to prevent.
        """
        real_id = _create_project(user_engine)

        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"99999"):
                prod_service.create_task(
                    session,
                    {"title": "Mixed", "status": "todo"},
                    project_ids=[real_id, 99999],
                )

        # Task must not have been created
        with _get_session(user_engine) as session:
            assert list(session.exec(select(Task)).all()) == []

    def test_create_task_accepts_all_valid_project_ids(self, user_engine):
        """Positive case: a list of valid IDs links correctly."""
        id_a = _create_project(user_engine)
        id_b = _create_project(user_engine)

        with _get_session(user_engine) as session:
            task = prod_service.create_task(
                session,
                {"title": "Two real links", "status": "todo"},
                project_ids=[id_a, id_b],
            )
        assert task is not None
        # Materialize the relationship inside the session, then read IDs
        # outside. Otherwise SQLAlchemy's lazy load fails because the
        # session is already closed by this point.
        with _get_session(user_engine) as session:
            task = session.get(Task, task.id)
            assert task is not None
            linked_ids = {p.id for p in task.projects}
        assert linked_ids == {id_a, id_b}

    def test_create_journal_rejects_missing_project_id(self, user_engine):
        """B1: a project-type journal must reference an existing project."""
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"Project 99999 not found"):
                prod_service.create_journal(
                    session,
                    {
                        "entry_type": "project",
                        "reference_date": date(2026, 6, 2),
                        "title": "Orphan",
                        "content": "x",
                        "project_id": 99999,
                    },
                )

    def test_create_journal_without_project_id_is_allowed(self, user_engine):
        """B1 (negative case): only project-typed journals may have a project_id.

        General / daily / etc. journals have no project_id by design.
        """
        with _get_session(user_engine) as session:
            journal = prod_service.create_journal(
                session,
                {
                    "entry_type": "general",
                    "reference_date": date(2026, 6, 2),
                    "title": "Standalone",
                    "content": "x",
                },
            )
        assert journal is not None
        assert journal.project_id is None

    def test_create_journal_with_valid_project_id_succeeds(self, user_engine):
        project_id = _create_project(user_engine)
        with _get_session(user_engine) as session:
            journal = prod_service.create_journal(
                session,
                {
                    "entry_type": "project",
                    "reference_date": date(2026, 6, 2),
                    "title": "Linked journal",
                    "content": "x",
                    "project_id": project_id,
                },
            )
        assert journal is not None
        assert journal.project_id == project_id

    def test_update_journal_rejects_missing_project_id(self, user_engine):
        """B2: re-linking a journal to a non-existent project must raise."""
        from genesis_core.productivity.models import JournalEntry

        project_id = _create_project(user_engine)
        journal_id: int | None = None
        with _get_session(user_engine) as session:
            j = prod_service.create_journal(
                session,
                {
                    "entry_type": "project",
                    "reference_date": date(2026, 6, 2),
                    "title": "Will be re-linked",
                    "content": "x",
                    "project_id": project_id,
                },
            )
            journal_id = j.id
        assert journal_id is not None

        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"Project 88888 not found"):
                prod_service.update_journal(session, journal_id, {"project_id": 88888})

        # Journal must be unchanged
        with _get_session(user_engine) as session:
            j = session.get(JournalEntry, journal_id)
            assert j is not None
            assert j.project_id == project_id

    def test_update_journal_allows_unlinking_with_none(self, user_engine):
        """B2 (positive case): setting project_id to None is allowed (unlink)."""

        project_id = _create_project(user_engine)
        journal_id: int | None = None
        with _get_session(user_engine) as session:
            j = prod_service.create_journal(
                session,
                {
                    "entry_type": "project",
                    "reference_date": date(2026, 6, 2),
                    "title": "Will be unlinked",
                    "content": "x",
                    "project_id": project_id,
                },
            )
            journal_id = j.id
        assert journal_id is not None

        with _get_session(user_engine) as session:
            updated = prod_service.update_journal(session, journal_id, {"project_id": None})
        assert updated is not None
        assert updated.project_id is None

    def test_bulk_update_tasks_rejects_missing_add_project_id(self, user_engine):
        """B4: every project to be added must exist."""
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"Project\(s\) not found"):
                prod_service.bulk_update_tasks(
                    session,
                    task_ids=[task_id],
                    field_updates={},
                    add_project_ids=[99999],
                )

        # Task must not have been mutated
        with _get_session(user_engine) as session:
            t = session.get(Task, task_id)
            assert t is not None
            assert list(t.projects) == []

    def test_bulk_update_tasks_remove_project_id_is_noop_on_missing(self, user_engine):
        """B4 (negative case): remove_project_ids with a missing ID is a no-op.

        Matches the current behavior and the existing test for the
        enum guard. We must not regress this.
        """
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            # No exception expected.
            count = prod_service.bulk_update_tasks(
                session,
                task_ids=[task_id],
                field_updates={},
                remove_project_ids=[99999],
            )
        assert count == 1

    def test_bulk_update_tasks_with_valid_add_project_id_succeeds(self, user_engine):
        project_id = _create_project(user_engine)
        task_id = _create_task(user_engine)
        with _get_session(user_engine) as session:
            count = prod_service.bulk_update_tasks(
                session,
                task_ids=[task_id],
                field_updates={},
                add_project_ids=[project_id],
            )
        assert count == 1
        with _get_session(user_engine) as session:
            t = session.get(Task, task_id)
            assert t is not None
            assert {p.id for p in t.projects} == {project_id}


class TestBlankStringGuards:
    """B5: title and name must be non-blank."""

    @pytest.mark.parametrize("title", ["", " ", "   ", "\t", "\n", "  \t\n "])
    def test_create_task_rejects_blank_title(self, user_engine, title):
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"title is required and must not be blank"):
                prod_service.create_task(session, {"title": title, "status": "todo"})

    def test_create_task_missing_title_rejected(self, user_engine):
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"title is required and must not be blank"):
                prod_service.create_task(session, {"status": "todo"})

    def test_create_task_non_string_title_rejected(self, user_engine):
        """A non-string title (e.g. a stray int) is also rejected."""
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"title is required and must not be blank"):
                prod_service.create_task(session, {"title": 42, "status": "todo"})

    def test_create_task_with_valid_title_succeeds(self, user_engine):
        with _get_session(user_engine) as session:
            task = prod_service.create_task(session, {"title": "Real", "status": "todo"})
        assert task is not None

    @pytest.mark.parametrize("name", ["", " ", "   ", "\t\n"])
    def test_create_project_rejects_blank_name(self, user_engine, name):
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"name is required and must not be blank"):
                prod_service.create_project(session, {"name": name})

    def test_create_project_missing_name_rejected(self, user_engine):
        with _get_session(user_engine) as session:
            with pytest.raises(ValueError, match=r"name is required and must not be blank"):
                prod_service.create_project(session, {})

    def test_create_project_with_valid_name_succeeds(self, user_engine):
        with _get_session(user_engine) as session:
            project = prod_service.create_project(session, {"name": "Real Project"})
        assert project is not None
