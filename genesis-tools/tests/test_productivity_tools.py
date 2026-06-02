"""Unit tests for productivity_tools module.

Focuses on EditJournalTool (surgical, overwrite, and error paths) and
SearchTasksTool pagination defaults. Uses a temporary SQLite database
per test session via the existing get_user_session context manager.
"""

import asyncio
import tempfile
from datetime import date
from pathlib import Path

import pytest
from genesis_core.productivity import service as prod_service
from genesis_core.productivity.db import _user_engines
from genesis_tools.productivity_tools import (
    CreateJournalTool,
    CreateProjectTool,
    CreateTaskTool,
    EditJournalTool,
    SearchTasksTool,
    UpdateProjectTool,
    UpdateTasksTool,
)


@pytest.fixture
def user_db_url():
    """Yield a fresh SQLite file URL per test, then clean up the engine cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"sqlite:///{Path(tmpdir) / 'user.db'}"
        yield url
        # Drop the engine from the global cache so the next test gets a fresh DB
        _user_engines.pop(url, None)


def _create_journal(
    user_db_url: str, content: str = "Original content.", title: str = "Test Journal"
) -> int:
    """Helper to create a journal and return its ID."""
    journal_id = None
    for session in get_session(user_db_url):
        journal = prod_service.create_journal(
            session,
            {
                "entry_type": "general",
                "reference_date": date(2026, 1, 1),
                "title": title,
                "content": content,
            },
        )
        journal_id = journal.id
    assert journal_id is not None
    return journal_id


def get_session(user_db_url: str):
    """Re-import here so the test stays self-contained and avoids a top-level import cycle."""
    from genesis_core.productivity.db import get_user_session

    return get_user_session(db_url=user_db_url)


def _run(tool, **kwargs):
    """Convenience wrapper to run an async tool with a fixed user_db_url."""
    return asyncio.run(tool.run(user_db_url=kwargs.pop("user_db_url"), **kwargs))


def _get_task(user_db_url: str, task_id: int):
    """Fetch a task and assert it exists (narrows the return type)."""
    from genesis_core.productivity.models import Task

    t: Task | None = None
    for session in get_session(user_db_url):
        t = prod_service.get_task(session, task_id)
    assert t is not None, f"Task {task_id} should exist"
    return t


def _get_journal(user_db_url: str, journal_id: int):
    """Fetch a journal and assert it exists (narrows the return type)."""
    from genesis_core.productivity.models import JournalEntry

    j: JournalEntry | None = None
    for session in get_session(user_db_url):
        j = prod_service.get_journal(session, journal_id)
    assert j is not None, f"Journal {journal_id} should exist"
    return j


def _get_project_id(user_db_url: str, name: str) -> int:
    """Fetch a project by name and return its ID."""
    from genesis_core.productivity.models import Project

    pid: int | None = None
    for session in get_session(user_db_url):
        proj: Project | None = session.exec(
            __import__("sqlmodel").select(Project).where(Project.name == name),
        ).first()
        if proj is not None:
            pid = proj.id
    assert pid is not None, f"Project {name} should exist"
    return pid


# --- EditJournalTool tests ---


class TestEditJournalToolSurgical:
    def test_surgical_replace_succeeds_with_unique_match(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Hello world. Goodnight moon.")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="world",
            new_str="universe",
        )
        assert result.status == "success"
        assert "edited successfully" in result.tool_response
        assert result.entities_to_track and result.entities_to_track[0].item_id == journal_id

        j = _get_journal(user_db_url, journal_id)
        assert j.content == "Hello universe. Goodnight moon."

    def test_surgical_replace_fails_when_string_not_found(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Hello world.")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="missing text",
            new_str="whatever",
        )
        assert result.status == "error"
        assert "Could not find" in result.tool_response

        j = _get_journal(user_db_url, journal_id)
        assert j.content == "Hello world."

    def test_surgical_replace_fails_on_ambiguous_match(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="foo bar foo")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="foo",
            new_str="baz",
        )
        assert result.status == "error"
        assert "2 occurrences" in result.tool_response
        assert "new_content" in result.tool_response  # Should suggest the overwrite path

    def test_surgical_replace_with_title_rename(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Body", title="Old Title")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="Body",
            new_str="Updated body",
            title="New Title",
        )
        assert result.status == "success"

        j = _get_journal(user_db_url, journal_id)
        assert j.title == "New Title"
        assert j.content == "Updated body"


class TestEditJournalToolOverwrite:
    def test_full_overwrite_replaces_content(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Original long body that should be wiped.")
        new_body = "Completely new content."
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            new_content=new_body,
        )
        assert result.status == "success"
        assert "overwritten successfully" in result.tool_response

        j = _get_journal(user_db_url, journal_id)
        assert j.content == new_body

    def test_overwrite_can_also_rename(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Old body.", title="Old Name")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            new_content="New body.",
            title="New Name",
        )
        assert result.status == "success"

        j = _get_journal(user_db_url, journal_id)
        assert j.content == "New body."
        assert j.title == "New Name"

    def test_overwrite_pins_journal_to_clipboard(self, user_db_url):
        journal_id = _create_journal(user_db_url, content="Old.")
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            new_content="Brand new.",
        )
        assert result.entities_to_track is not None
        assert len(result.entities_to_track) == 1
        entity = result.entities_to_track[0]
        assert entity.item_type == "journal"
        assert entity.item_id == journal_id
        assert entity.resolution == "detail"
        assert entity.ttl == 10


class TestEditJournalToolValidation:
    def test_both_modes_specified_is_error(self, user_db_url):
        journal_id = _create_journal(user_db_url)
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="x",
            new_str="y",
            new_content="z",
        )
        assert result.status == "error"
        assert "Ambiguous content mode" in result.tool_response

    def test_no_content_update_is_error(self, user_db_url):
        journal_id = _create_journal(user_db_url)
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
        )
        assert result.status == "error"
        assert "Missing content update" in result.tool_response

    def test_surgical_mode_requires_both_old_and_new(self, user_db_url):
        journal_id = _create_journal(user_db_url)
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="x",
        )
        assert result.status == "error"
        assert "requires BOTH" in result.tool_response

    def test_missing_journal_id_is_error(self, user_db_url):
        result = _run(EditJournalTool(), user_db_url=user_db_url, new_content="anything")
        assert result.status == "error"
        assert "journal_id" in result.tool_response

    def test_missing_database_returns_error(self):
        result = _run(EditJournalTool(), user_db_url=None, journal_id=1, new_content="x")
        assert result.status == "error"
        assert "Database connection" in result.tool_response

    def test_nonexistent_journal_returns_error(self, user_db_url):
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=9999,
            new_content="anything",
        )
        assert result.status == "error"
        assert "not found" in result.tool_response


# --- SearchTasksTool tests ---


class TestSearchTasksToolDefaults:
    def test_default_limit_is_100(self):
        """The default limit is documented as 100 so the agent gets a full project view."""
        # 1. Confirm parameter schema describes the default
        assert "Default is 100" in SearchTasksTool.parameters["properties"]["limit"]["description"]

        # 2. Confirm the run() method uses 100 as the default by parsing the source
        import inspect

        sig = inspect.signature(SearchTasksTool.run)
        # `limit` is set via kwargs.get, not a default argument. So we
        # assert the schema description is the contract the LLM sees.
        # The behaviour default is verified via the integration test below.
        assert sig.parameters  # just confirm signature exists

    def test_default_limit_applied_when_omitted(self, user_db_url):
        """When the agent omits 'limit', the tool should still cap at 100."""
        # Create 105 tasks linked to a project so 100 is meaningful
        project_id = None
        for session in get_session(user_db_url):
            project = prod_service.create_project(session, {"name": "Big Project"})
            project_id = project.id
            assert project_id is not None
            for i in range(105):
                prod_service.create_task(
                    session,
                    {"title": f"Task {i:03d}", "status": "todo"},
                    project_ids=[project_id],
                )

        result = _run(
            SearchTasksTool(),
            user_db_url=user_db_url,
            project_id=project_id,
        )
        assert result.status == "success"
        assert "Found 100 tasks" in result.tool_response
        assert len(result.entities_to_track) == 100

    def test_explicit_limit_overrides_default(self, user_db_url):
        project_id = None
        for session in get_session(user_db_url):
            project = prod_service.create_project(session, {"name": "Small Project"})
            project_id = project.id
            assert project_id is not None
            for i in range(10):
                prod_service.create_task(
                    session,
                    {"title": f"T{i}", "status": "todo"},
                    project_ids=[project_id],
                )

        result = _run(
            SearchTasksTool(),
            user_db_url=user_db_url,
            project_id=project_id,
            limit=3,
        )
        assert result.status == "success"
        assert "Found 3 tasks" in result.tool_response
        assert len(result.entities_to_track) == 3

    def test_description_includes_four_worked_examples(self):
        """The description must lead with concrete recipes for common queries."""
        desc = SearchTasksTool.description
        assert "WORKED EXAMPLES" in desc
        # All four canonical patterns from the user must be present
        assert "All open tasks of a project" in desc
        assert "assigned today or overdue" in desc
        assert "Appointments this week" in desc
        assert "deadline this week" in desc
        # Pointer to compute_date_range
        assert "compute_date_range" in desc


# --- EditJournalTool metadata behavior ---


class TestEditJournalToolSchema:
    def test_required_is_only_journal_id(self):
        """old_str and new_str must be optional so overwrite mode is selectable."""
        assert EditJournalTool.parameters["required"] == ["journal_id"]

    def test_new_content_property_exists(self):
        props = EditJournalTool.parameters["properties"]
        assert "new_content" in props
        assert props["new_content"]["type"] == "string"


# --- Enum-typed status guard (regression for the corrupt-task-list bug) ---


class TestStatusEnumGuard:
    """Regression tests for the corrupt-task-list bug.

    The agent previously wrote `status='deleted'` to tasks because the tool
    schemas did not declare an `enum` and the runtime accepted any string.
    These tests pin down the three-layer defense: schema enum, runtime
    guard in `run()`, and a service-layer guard (covered separately).
    """

    @pytest.mark.parametrize(
        "tool_cls", [CreateTaskTool, UpdateTasksTool, CreateProjectTool, UpdateProjectTool]
    )
    def test_status_schema_has_enum_constraint(self, tool_cls):
        """Layer 1: every status-accepting tool declares the JSON schema enum."""
        props = tool_cls.parameters["properties"]
        assert "status" in props, f"{tool_cls.__name__} has no status field"
        status_schema = props["status"]
        assert status_schema["type"] == "string"
        assert "enum" in status_schema, (
            f"{tool_cls.__name__}.parameters.properties.status is missing 'enum'"
        )
        # The enum list must include every Status enum value
        from genesis_core.productivity.models import Status

        assert set(status_schema["enum"]) == {s.value for s in Status}

    def test_create_task_rejects_invalid_status(self, user_db_url):
        """Layer 2: CreateTaskTool returns an error and does not write to DB."""
        result = _run(
            CreateTaskTool(),
            user_db_url=user_db_url,
            title="Should not be created",
            status="deleted",  # not in the Status enum
        )
        assert result.status == "error"
        assert "Invalid status" in result.tool_response
        assert "deleted" in result.tool_response

        # Confirm nothing was written
        from genesis_core.productivity.models import Task
        from sqlmodel import select as _select

        rows = []
        for session in get_session(user_db_url):
            rows = list(session.exec(_select(Task)).all())
        assert rows == [], "Task must not be created when status is invalid"

    def test_update_tasks_rejects_invalid_status(self, user_db_url):
        """Layer 2: UpdateTasksTool returns an error and does not mutate any task."""
        # Seed a task with a valid status
        task_id = None
        for session in get_session(user_db_url):
            task = prod_service.create_task(session, {"title": "Existing", "status": "todo"})
            task_id = task.id
        assert task_id is not None

        result = _run(
            UpdateTasksTool(),
            user_db_url=user_db_url,
            task_ids=[task_id],
            status="deleted",
        )
        assert result.status == "error"
        assert "Invalid status" in result.tool_response

        # Confirm the task was not mutated
        task = _get_task(user_db_url, task_id)
        assert task.status == "todo"

    def test_update_tasks_accepts_all_valid_statuses(self, user_db_url):
        """Layer 2: every value in the Status enum is accepted (no false positives)."""
        from genesis_core.productivity.models import Status

        for status_value in [s.value for s in Status]:
            task_id = None
            for session in get_session(user_db_url):
                task = prod_service.create_task(
                    session,
                    {"title": f"Task-{status_value}", "status": "todo"},
                )
                task_id = task.id
            assert task_id is not None

            result = _run(
                UpdateTasksTool(),
                user_db_url=user_db_url,
                task_ids=[task_id],
                status=status_value,
            )
            assert result.status == "success", (
                f"status={status_value!r} should be accepted but got: {result.tool_response}"
            )

    def test_create_project_rejects_invalid_status(self, user_db_url):
        result = _run(
            CreateProjectTool(),
            user_db_url=user_db_url,
            name="Should not be created",
            status="archived",  # not in the Status enum
        )
        assert result.status == "error"
        assert "Invalid status" in result.tool_response

    def test_update_project_rejects_invalid_status(self, user_db_url):
        project_id = None
        for session in get_session(user_db_url):
            project = prod_service.create_project(session, {"name": "Existing"})
            project_id = project.id
        assert project_id is not None

        result = _run(
            UpdateProjectTool(),
            user_db_url=user_db_url,
            project_id=project_id,
            status="archived",
        )
        assert result.status == "error"
        assert "Invalid status" in result.tool_response

    def test_missing_status_is_still_allowed(self, user_db_url):
        """Layer 2: the guard only triggers on present-but-invalid, not on omitted.

        A tool call without `status` must continue to default to the
        service-layer default (or leave the field untouched for updates).
        """
        result = _run(
            CreateTaskTool(),
            user_db_url=user_db_url,
            title="No status provided",
        )
        assert result.status == "success"


# --- Foreign-key and blank-string guards (B1-B5) at the tool layer ---


class TestForeignKeyGuardsAtTool:
    """B1-B4: the tool must surface service-layer FK errors cleanly."""

    def test_create_journal_rejects_missing_project_id(self, user_db_url):
        """B1."""
        result = _run(
            CreateJournalTool(),
            user_db_url=user_db_url,
            entry_type="project",
            reference_date="2026-06-02",
            content="x",
            project_id=99999,
        )
        assert result.status == "error"
        assert "Project 99999 not found" in result.tool_response
        # No journal was created
        from genesis_core.productivity.models import JournalEntry
        from sqlmodel import select as _select

        rows = []
        for session in get_session(user_db_url):
            rows = list(session.exec(_select(JournalEntry)).all())
        assert rows == []

    def test_create_journal_with_valid_project_id_succeeds(self, user_db_url):
        """B1 positive case."""
        for session in get_session(user_db_url):
            prod_service.create_project(session, {"name": "Real Project"})
        project_id = _get_project_id(user_db_url, "Real Project")

        result = _run(
            CreateJournalTool(),
            user_db_url=user_db_url,
            entry_type="project",
            reference_date="2026-06-02",
            content="x",
            project_id=project_id,
        )
        assert result.status == "success"

    def test_edit_journal_rejects_missing_project_id(self, user_db_url):
        """B2."""
        journal_id = _create_journal(user_db_url)
        result = _run(
            EditJournalTool(),
            user_db_url=user_db_url,
            journal_id=journal_id,
            old_str="Original",
            new_str="Replaced",
            project_id=88888,
        )
        assert result.status == "error"
        assert "Project 88888 not found" in result.tool_response

        # Journal must not have been modified
        j = _get_journal(user_db_url, journal_id)
        assert j.content == "Original content."
        assert j.project_id is None

    def test_create_task_rejects_missing_project_id(self, user_db_url):
        """B3."""
        result = _run(
            CreateTaskTool(),
            user_db_url=user_db_url,
            title="Linked to ghost",
            project_ids=[99999],
        )
        assert result.status == "error"
        assert "Project(s) not found" in result.tool_response
        assert "99999" in result.tool_response

    def test_create_task_rejects_mixed_valid_and_missing_project_ids(self, user_db_url):
        """B3 (multi-ID): the whole call fails, no partial link created."""
        for session in get_session(user_db_url):
            prod_service.create_project(session, {"name": "Real Project"})
        real_id = _get_project_id(user_db_url, "Real Project")

        result = _run(
            CreateTaskTool(),
            user_db_url=user_db_url,
            title="Mixed links",
            project_ids=[real_id, 99999],
        )
        assert result.status == "error"
        assert "99999" in result.tool_response
        # The real project link must not have been created either.
        from genesis_core.productivity.models import Task
        from sqlmodel import select as _select

        tasks: list[Task] = []
        for session in get_session(user_db_url):
            tasks = list(session.exec(_select(Task)).all())
        assert tasks == []

    def test_update_tasks_rejects_missing_add_project_id(self, user_db_url):
        """B4."""
        task_id = None
        for session in get_session(user_db_url):
            task = prod_service.create_task(session, {"title": "Existing", "status": "todo"})
            task_id = task.id
        assert task_id is not None

        result = _run(
            UpdateTasksTool(),
            user_db_url=user_db_url,
            task_ids=[task_id],
            add_project_ids=[55555],
        )
        assert result.status == "error"
        assert "Project(s) not found" in result.tool_response
        assert "55555" in result.tool_response

        # Task must not have been linked
        t = _get_task(user_db_url, task_id)
        assert list(t.projects) == []

    def test_update_tasks_remove_project_id_with_missing_id_is_noop(self, user_db_url):
        """B4 (negative case): remove_project_ids with missing ID is fine."""
        task_id = None
        for session in get_session(user_db_url):
            task = prod_service.create_task(session, {"title": "Existing", "status": "todo"})
            task_id = task.id
        assert task_id is not None

        result = _run(
            UpdateTasksTool(),
            user_db_url=user_db_url,
            task_ids=[task_id],
            remove_project_ids=[99999],
        )
        assert result.status == "success"


class TestBlankStringGuardsAtTool:
    """B5: title and name must not be blank."""

    @pytest.mark.parametrize("blank", ["", " ", "  \t\n "])
    def test_create_task_rejects_blank_title(self, user_db_url, blank):
        result = _run(CreateTaskTool(), user_db_url=user_db_url, title=blank)
        assert result.status == "error"
        assert "title is required and must not be blank" in result.tool_response

    @pytest.mark.parametrize("blank", ["", " ", "  \t\n "])
    def test_create_project_rejects_blank_name(self, user_db_url, blank):
        result = _run(CreateProjectTool(), user_db_url=user_db_url, name=blank)
        assert result.status == "error"
        assert "name is required and must not be blank" in result.tool_response
