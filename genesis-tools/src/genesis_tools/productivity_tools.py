import zoneinfo
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from genesis_core.productivity import service as prod_service
from genesis_core.productivity.db import get_user_session
from genesis_core.productivity.models import JournalEntry, JournalType, Project, ProjectTaskLink, Task
from sqlmodel import and_, col, or_, select

from .base import BaseTool
from .schema import ToolResult, TrackedEntity


def _parse_to_utc(date_str: str, is_end_of_day: bool, local_tz: str) -> datetime:
    """Helper to convert agent date/time strings into UTC datetimes for database querying.
    If only YYYY-MM-DD is provided, expands it to 00:00:00 or 23:59:59 in the local timezone.
    """
    tz = zoneinfo.ZoneInfo(local_tz)

    # If it's just a date string (YYYY-MM-DD)
    if len(date_str) == 10:
        dt_date = date.fromisoformat(date_str)
        if is_end_of_day:
            # End of the specific day
            dt_time = time(23, 59, 59, 999999)
        else:
            # Start of the specific day
            dt_time = time(0, 0, 0)

        local_dt = datetime.combine(dt_date, dt_time, tzinfo=tz)
        return local_dt.astimezone(UTC)

    # If it's a full ISO timestamp
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        # Assume it was provided in the local timezone if naive
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(UTC)


class SearchTasksTool(BaseTool):
    name = "search_tasks"
    description = (
        "Search and filter the user's tasks. The results will be pinned to your CLIPBOARD. "
        "CRITICAL SEARCH BEHAVIOR: "
        "1. By default, date/text filters are combined using 'OR'. If you want strict matching, change 'query_logic' to 'AND'. "
        "2. If you provide a date (YYYY-MM-DD), it automatically covers the entire 24-hour day in the user's timezone. "
        "3. To search for a specific day, pass BOTH start and end parameters with the SAME date. "
        "DATA FIELDS: "
        "- 'assigned_date': The floating calendar day the user plans to do the task. "
        "- 'hard_deadline': The absolute timestamp the task is due. "
        "- 'scheduled_start': The absolute timestamp for an appointment."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "How to combine the search filters (dates, project, text). Default is 'OR'.",
            },
            "status": {
                "type": "string",
                "description": "Base filter. 'todo', 'in_progress', 'completed', 'backlog'. Omitting fetches ALL INCOMPLETE tasks.",
            },
            "search_query": {
                "type": "string",
                "description": "Text search across task title and description.",
            },
            "project_id": {
                "type": "integer",
                "description": "Filter tasks belonging to a specific project ID.",
            },
            "assigned_date_start": {
                "type": "string",
                "description": "YYYY-MM-DD. Tasks planned on or after this date.",
            },
            "assigned_date_end": {
                "type": "string",
                "description": "YYYY-MM-DD. Tasks planned on or before this date.",
            },
            "deadline_start": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. Tasks due on or after this date.",
            },
            "deadline_end": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. Tasks due on or before this date.",
            },
            "scheduled_start_start": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. Appointments on or after this date.",
            },
            "scheduled_start_end": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. Appointments on or before this date.",
            },
            "limit": {"type": "integer", "description": "Pagination limit. Default is 20."},
            "offset": {
                "type": "integer",
                "description": "Pagination offset (number of tasks to skip). Default is 0.",
            },
        },
        "additionalProperties": False,
    }

    async def run(self, user_db_url: str | None = None, timezone: str = "UTC", **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)
        logic = kwargs.get("query_logic", "OR").upper()
        status = kwargs.get("status")

        statement = select(Task)

        # 1. BASE FILTERS (Always ANDed)
        if status:
            statement = statement.where(col(Task.status) == status)
        else:
            statement = statement.where(col(Task.status) != "completed")

        if kwargs.get("project_id"):
            statement = statement.join(ProjectTaskLink).where(
                col(ProjectTaskLink.project_id) == kwargs.get("project_id"),
            )

        # 2. DYNAMIC FILTERS (Combined via query_logic)
        dynamic_conditions = []

        # Text Search
        search_query = kwargs.get("search_query")
        if search_query:
            search_pattern = f"%{search_query}%"
            dynamic_conditions.append(
                or_(col(Task.title).like(search_pattern), col(Task.description).like(search_pattern)),
            )

        # Assigned Date
        assigned_start = kwargs.get("assigned_date_start")
        assigned_end = kwargs.get("assigned_date_end")
        assigned_conds = []
        if assigned_start:
            assigned_conds.append(col(Task.assigned_date) >= date.fromisoformat(assigned_start[:10]))
        if assigned_end:
            assigned_conds.append(col(Task.assigned_date) <= date.fromisoformat(assigned_end[:10]))
        if assigned_conds:
            dynamic_conditions.append(and_(*assigned_conds))

        # Hard Deadline
        deadline_start = kwargs.get("deadline_start")
        deadline_end = kwargs.get("deadline_end")
        deadline_conds = []
        if deadline_start:
            utc_dt = _parse_to_utc(deadline_start, is_end_of_day=False, local_tz=timezone)
            deadline_conds.append(col(Task.hard_deadline) >= utc_dt)
        if deadline_end:
            utc_dt = _parse_to_utc(deadline_end, is_end_of_day=True, local_tz=timezone)
            deadline_conds.append(col(Task.hard_deadline) <= utc_dt)
        if deadline_conds:
            dynamic_conditions.append(and_(*deadline_conds))

        # Scheduled Start
        scheduled_start = kwargs.get("scheduled_start_start")
        scheduled_end = kwargs.get("scheduled_start_end")
        scheduled_conds = []
        if scheduled_start:
            utc_dt = _parse_to_utc(scheduled_start, is_end_of_day=False, local_tz=timezone)
            scheduled_conds.append(col(Task.scheduled_start) >= utc_dt)
        if scheduled_end:
            utc_dt = _parse_to_utc(scheduled_end, is_end_of_day=True, local_tz=timezone)
            scheduled_conds.append(col(Task.scheduled_start) <= utc_dt)
        if scheduled_conds:
            dynamic_conditions.append(and_(*scheduled_conds))

        # Apply Dynamic Conditions
        if dynamic_conditions:
            if logic == "AND":
                statement = statement.where(and_(*dynamic_conditions))
            else:
                statement = statement.where(or_(*dynamic_conditions))

        # 3. Default Sorting
        statement = (
            statement.order_by(
                col(Task.status).desc(),
                col(Task.hard_deadline).asc(),
                col(Task.assigned_date).asc(),
                col(Task.scheduled_start).asc(),
                col(Task.created_at).asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        try:
            # 4. Execute Query
            task_ids = []
            for session in get_user_session(db_url=user_db_url):
                results = session.exec(statement).all()
                task_ids = [t.id for t in results if t.id is not None]

            if not task_ids:
                return ToolResult(
                    status="success",
                    tool_response="Search completed. No tasks found matching those criteria.",
                )

            # 5. Signal the Agent Loop
            entities = [
                TrackedEntity(item_type="task", item_id=t_id, resolution="summary", ttl=10)
                for t_id in task_ids
            ]

            return ToolResult(
                status="success",
                tool_response=f"Found {len(task_ids)} tasks. They have been pinned to your CLIPBOARD. Read your clipboard context to see them.",
                entities_to_track=entities,
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date parsing error: {e!s}")
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e!s}")


class ReadTaskTool(BaseTool):
    name = "read_task"
    description = (
        "Retrieves the full, detailed record of a specific task, including its description and project links. "
        "The details will be pinned to your CLIPBOARD. Use this when you need to understand exactly what a task entails."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",
                "description": "The ID of the task to read.",
            },
        },
        "required": ["task_id"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        task_id = kwargs.get("task_id")
        if not task_id or not user_db_url:
            return ToolResult(status="error", tool_response="Missing task_id or DB connection.")

        # We verify the task exists using the core service before pinning
        try:
            for session in get_user_session(db_url=user_db_url):
                task = session.get(Task, task_id)
                if not task:
                    return ToolResult(status="error", tool_response=f"Task ID {task_id} not found.")

            # Pin as DETAIL mode so the LLM gets the full description rendered
            entity = TrackedEntity(item_type="task", item_id=task_id, resolution="detail", ttl=10)

            return ToolResult(
                status="success",
                tool_response=f"Task {task_id} details have been pinned to your CLIPBOARD. Check the 'USER PRODUCTIVITY SYSTEM' section.",
                entities_to_track=[entity],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to read task: {e!s}")


# --- PROJECT TOOLS ---


class SearchProjectsTool(BaseTool):
    name = "search_projects"
    description = (
        "Search and filter the user's projects. The results will be pinned to your CLIPBOARD. "
        "By default, dynamic filters (dates, text) are combined using 'OR'. "
        "Dates for projects are floating calendar dates (YYYY-MM-DD)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "How to combine dynamic filters (text, dates). Default is 'OR'.",
            },
            "status": {
                "type": "string",
                "description": "Base filter. 'todo', 'in_progress', 'completed', 'canceled'. Omitting fetches ALL ACTIVE (not completed/canceled) projects.",
            },
            "search_query": {
                "type": "string",
                "description": "Text search across project name and description.",
            },
            "deadline_start": {
                "type": "string",
                "description": "YYYY-MM-DD. Projects due on or after this date.",
            },
            "deadline_end": {
                "type": "string",
                "description": "YYYY-MM-DD. Projects due on or before this date.",
            },
            "start_date_start": {
                "type": "string",
                "description": "YYYY-MM-DD. Projects starting on or after this date.",
            },
            "start_date_end": {
                "type": "string",
                "description": "YYYY-MM-DD. Projects starting on or before this date.",
            },
            "limit": {"type": "integer", "description": "Pagination limit. Default is 20."},
            "offset": {"type": "integer", "description": "Pagination offset. Default is 0."},
        },
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)
        logic = kwargs.get("query_logic", "OR").upper()
        status = kwargs.get("status")

        statement = select(Project)

        # 1. BASE FILTERS
        if status:
            statement = statement.where(col(Project.status) == status)
        else:
            statement = statement.where(col(Project.status).notin_(["completed", "canceled"]))

        # 2. DYNAMIC FILTERS
        dynamic_conditions = []

        search_query = kwargs.get("search_query")
        if search_query:
            search_pattern = f"%{search_query}%"
            dynamic_conditions.append(
                or_(col(Project.name).like(search_pattern), col(Project.description).like(search_pattern)),
            )

        deadline_start = kwargs.get("deadline_start")
        deadline_end = kwargs.get("deadline_end")
        deadline_conds = []
        if deadline_start:
            deadline_conds.append(col(Project.deadline) >= date.fromisoformat(deadline_start[:10]))
        if deadline_end:
            deadline_conds.append(col(Project.deadline) <= date.fromisoformat(deadline_end[:10]))
        if deadline_conds:
            dynamic_conditions.append(and_(*deadline_conds))

        start_date_start = kwargs.get("start_date_start")
        start_date_end = kwargs.get("start_date_end")
        start_conds = []
        if start_date_start:
            start_conds.append(col(Project.start_date) >= date.fromisoformat(start_date_start[:10]))
        if start_date_end:
            start_conds.append(col(Project.start_date) <= date.fromisoformat(start_date_end[:10]))
        if start_conds:
            dynamic_conditions.append(and_(*start_conds))

        if dynamic_conditions:
            if logic == "AND":
                statement = statement.where(and_(*dynamic_conditions))
            else:
                statement = statement.where(or_(*dynamic_conditions))

        # 3. Default Sorting (Active/soonest first)
        statement = (
            statement.order_by(
                col(Project.status).desc(), col(Project.deadline).asc(), col(Project.name).asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        try:
            project_ids = []
            for session in get_user_session(db_url=user_db_url):
                results = session.exec(statement).all()
                project_ids = [p.id for p in results if p.id is not None]

            if not project_ids:
                return ToolResult(status="success", tool_response="No projects found matching criteria.")

            entities = [
                TrackedEntity(item_type="project", item_id=p_id, resolution="summary", ttl=10)
                for p_id in project_ids
            ]
            return ToolResult(
                status="success",
                tool_response=f"Pinned {len(project_ids)} projects to CLIPBOARD.",
                entities_to_track=entities,
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e!s}")


class ReadProjectTool(BaseTool):
    name = "read_project"
    description = "Retrieves the full details of a specific project and pins it to your CLIPBOARD."
    parameters = {
        "type": "object",
        "properties": {"project_id": {"type": "integer", "description": "The ID of the project to read."}},
        "required": ["project_id"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        project_id = kwargs.get("project_id")
        if not project_id or not user_db_url:
            return ToolResult(status="error", tool_response="Missing project_id or DB connection.")

        try:
            for session in get_user_session(db_url=user_db_url):
                if not session.get(Project, project_id):
                    return ToolResult(status="error", tool_response=f"Project {project_id} not found.")

            entity = TrackedEntity(item_type="project", item_id=project_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Project {project_id} details pinned to CLIPBOARD.",
                entities_to_track=[entity],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to read project: {e!s}")


# --- JOURNAL TOOLS ---


class SearchJournalsTool(BaseTool):
    name = "search_journals"
    description = (
        "Search and filter the user's journal entries. The results will be pinned to your CLIPBOARD as summaries. "
        "Journals are sorted from newest to oldest by default. "
        "To read the full text of a journal, use read_journal on the resulting IDs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_logic": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "How to combine dynamic filters (text, dates). Default is 'OR'.",
            },
            "entry_type": {
                "type": "string",
                "description": "Base filter. e.g., 'daily', 'weekly', 'monthly', 'project', 'general'. Omitting fetches all types.",
            },
            "project_id": {
                "type": "integer",
                "description": "Base filter. Fetch journals linked to a specific project.",
            },
            "search_query": {
                "type": "string",
                "description": "Text search across journal title and markdown content.",
            },
            "reference_date_start": {
                "type": "string",
                "description": "YYYY-MM-DD. Journals referencing dates on or after this.",
            },
            "reference_date_end": {
                "type": "string",
                "description": "YYYY-MM-DD. Journals referencing dates on or before this.",
            },
            "limit": {"type": "integer", "description": "Pagination limit. Default is 10."},
            "offset": {"type": "integer", "description": "Pagination offset. Default is 0."},
        },
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        print(kwargs)
        limit = kwargs.get("limit", 10)  # Journals can be long, default limit to 10
        offset = kwargs.get("offset", 0)
        logic = kwargs.get("query_logic", "OR").upper()

        statement = select(JournalEntry)

        # 1. BASE FILTERS
        if kwargs.get("entry_type"):
            statement = statement.where(col(JournalEntry.entry_type) == kwargs.get("entry_type"))
        if kwargs.get("project_id"):
            statement = statement.where(col(JournalEntry.project_id) == kwargs.get("project_id"))

        # 2. DYNAMIC FILTERS
        dynamic_conditions = []

        search_query = kwargs.get("search_query")
        if search_query:
            search_pattern = f"%{search_query}%"
            dynamic_conditions.append(
                or_(
                    col(JournalEntry.title).like(search_pattern),
                    col(JournalEntry.content).like(search_pattern),
                ),
            )

        ref_date_start = kwargs.get("reference_date_start")
        ref_date_end = kwargs.get("reference_date_end")

        # Group the date range together
        date_conditions = []
        if ref_date_start:
            date_conditions.append(
                col(JournalEntry.reference_date) >= date.fromisoformat(ref_date_start[:10]),
            )
        if ref_date_end:
            date_conditions.append(
                col(JournalEntry.reference_date) <= date.fromisoformat(ref_date_end[:10]),
            )

        if date_conditions:
            # The start and end bounds of a single field must ALWAYS be ANDed
            dynamic_conditions.append(and_(*date_conditions))

        if dynamic_conditions:
            if logic == "AND":
                statement = statement.where(and_(*dynamic_conditions))
            else:
                statement = statement.where(or_(*dynamic_conditions))

        # 3. Default Sorting (Newest journals first)
        statement = (
            statement.order_by(col(JournalEntry.reference_date).desc(), col(JournalEntry.created_at).desc())
            .limit(limit)
            .offset(offset)
        )

        try:
            journal_ids = []
            for session in get_user_session(db_url=user_db_url):
                results = session.exec(statement).all()
                journal_ids = [j.id for j in results if j.id is not None]

            if not journal_ids:
                return ToolResult(status="success", tool_response="No journals found matching criteria.")

            # Pin as SUMMARY (Full text won't be in the prompt until they use read_journal)
            entities = [
                TrackedEntity(item_type="journal", item_id=j_id, resolution="summary", ttl=10)
                for j_id in journal_ids
            ]
            return ToolResult(
                status="success",
                tool_response=f"Pinned {len(journal_ids)} journal summaries to CLIPBOARD.",
                entities_to_track=entities,
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {e!s}")


class ReadJournalTool(BaseTool):
    name = "read_journal"
    description = (
        "Retrieves the full markdown text of a specific journal entry and pins it to your CLIPBOARD."
    )
    parameters = {
        "type": "object",
        "properties": {"journal_id": {"type": "integer", "description": "The ID of the journal to read."}},
        "required": ["journal_id"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        journal_id = kwargs.get("journal_id")
        if not journal_id or not user_db_url:
            return ToolResult(status="error", tool_response="Missing journal_id or DB connection.")

        try:
            for session in get_user_session(db_url=user_db_url):
                if not session.get(JournalEntry, journal_id):
                    return ToolResult(status="error", tool_response=f"Journal {journal_id} not found.")

            entity = TrackedEntity(item_type="journal", item_id=journal_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Journal {journal_id} content pinned to CLIPBOARD.",
                entities_to_track=[entity],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to read journal: {e!s}")


# --- CREATION TOOLS ---


class CreateTaskTool(BaseTool):
    name = "create_task"
    description = (
        "Creates a new task in the productivity system and pins it to your CLIPBOARD. "
        "Use this when the user asks you to remember to do something, schedule an appointment, or set a deadline."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title or name of the task."},
            "description": {"type": "string", "description": "Markdown description or notes for the task."},
            "status": {
                "type": "string",
                "description": "Status: 'todo', 'in_progress', 'completed', 'backlog'. Default is 'todo'.",
            },
            "assigned_date": {
                "type": "string",
                "description": "YYYY-MM-DD. The day the user plans to work on this.",
            },
            "hard_deadline": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. The absolute deadline.",
            },
            "scheduled_start": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. The time of an appointment/event.",
            },
            "project_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "A list of project IDs this task belongs to.",
            },
        },
        "required": ["title"],
    }

    async def run(self, user_db_url: str | None = None, timezone: str = "UTC", **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        data = {"title": kwargs["title"]}
        if "description" in kwargs:
            data["description"] = kwargs["description"]
        if "status" in kwargs:
            data["status"] = kwargs["status"]

        if kwargs.get("assigned_date"):
            data["assigned_date"] = date.fromisoformat(kwargs["assigned_date"][:10])

        try:
            if kwargs.get("hard_deadline"):
                data["hard_deadline"] = _parse_to_utc(
                    kwargs["hard_deadline"], is_end_of_day=True, local_tz=timezone,
                )
            if kwargs.get("scheduled_start"):
                data["scheduled_start"] = _parse_to_utc(
                    kwargs["scheduled_start"], is_end_of_day=False, local_tz=timezone,
                )
        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date formatting error: {e!s}")

        project_ids = kwargs.get("project_ids", [])

        task_id: int | None = None
        try:
            for session in get_user_session(db_url=user_db_url):
                task = prod_service.create_task(session, data, project_ids)
                task_id = task.id

            if task_id is None:  # Type Guard to fix "int | None"
                return ToolResult(status="error", tool_response="Failed to generate Task ID.")

            # Pin the newly created task to the clipboard in DETAIL mode
            entity = TrackedEntity(item_type="task", item_id=task_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Task '{data['title']}' created successfully with ID {task_id}. It is now pinned to your CLIPBOARD.",
                entities_to_track=[entity],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to create task: {e!s}")


class CreateProjectTool(BaseTool):
    name = "create_project"
    description = "Creates a new project and pins it to your CLIPBOARD. Projects are used to group related tasks and journals."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name of the project."},
            "description": {
                "type": "string",
                "description": "Markdown description or goals for the project.",
            },
            "status": {
                "type": "string",
                "description": "'todo', 'in_progress', 'completed', 'canceled'. Default is 'todo'.",
            },
            "start_date": {"type": "string", "description": "YYYY-MM-DD. When the project starts."},
            "deadline": {"type": "string", "description": "YYYY-MM-DD. When the project is due."},
        },
        "required": ["name"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        data = {"name": kwargs["name"]}
        if "description" in kwargs:
            data["description"] = kwargs["description"]
        if "status" in kwargs:
            data["status"] = kwargs["status"]

        try:
            if kwargs.get("start_date"):
                data["start_date"] = date.fromisoformat(kwargs["start_date"][:10])
            if kwargs.get("deadline"):
                data["deadline"] = date.fromisoformat(kwargs["deadline"][:10])
        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date parsing error: {e!s}")

        project_id: int | None = None
        try:
            for session in get_user_session(db_url=user_db_url):
                project = prod_service.create_project(session, data)
                project_id = project.id

            if project_id is None:
                return ToolResult(status="error", tool_response="Failed to generate Project ID.")

            entity = TrackedEntity(item_type="project", item_id=project_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Project '{data['name']}' created successfully with ID {project_id}. It is pinned to your CLIPBOARD.",
                entities_to_track=[entity],
            )
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to create project: {e!s}")


class CreateJournalTool(BaseTool):
    name = "create_journal"
    description = (
        "Creates a new journal entry (daily, weekly, monthly, yearly, project, or general). "
        "The system will automatically normalize the reference_date (e.g., weekly journals always snap to the Monday of that week). "
        "If a journal of that type and date already exists, this tool will reject the creation and give you its ID to read/update instead."
    )
    parameters = {
        "type": "object",
        "properties": {
            "entry_type": {
                "type": "string",
                "enum": ["daily", "weekly", "monthly", "yearly", "project", "general"],
                "description": "The type of journal.",
            },
            "reference_date": {
                "type": "string",
                "description": "YYYY-MM-DD. The date this journal is about. If weekly/monthly/yearly, just pass any date within that period.",
            },
            "content": {"type": "string", "description": "The Markdown body of the journal."},
            "title": {
                "type": "string",
                "description": "Optional custom title. If omitted, one is auto-generated.",
            },
            "project_id": {"type": "integer", "description": "REQUIRED if entry_type is 'project'."},
        },
        "required": ["entry_type", "reference_date", "content"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        entry_type_str = kwargs["entry_type"]
        entry_type_enum = JournalType(entry_type_str)

        content = kwargs["content"]

        if entry_type_str == "project" and not kwargs.get("project_id"):
            return ToolResult(
                status="error", tool_response="project_id is required when entry_type is 'project'.",
            )

        journal_id: int | None = None

        try:
            # 1. Normalize the reference date
            raw_date_str = kwargs["reference_date"][:10]
            ref_date = date.fromisoformat(raw_date_str)

            if entry_type_str == "weekly":
                ref_date = ref_date - timedelta(days=ref_date.weekday())
            elif entry_type_str == "monthly":
                ref_date = ref_date.replace(day=1)
            elif entry_type_str == "yearly":
                ref_date = ref_date.replace(month=1, day=1)

            ref_date_str = ref_date.isoformat()

            # 2. Handle Title
            title = kwargs.get("title")
            if not title:
                title = f"{entry_type_str.capitalize()} - {ref_date_str}"

            data = {
                "entry_type": entry_type_str,
                "reference_date": ref_date,
                "title": title,
                "content": content,
            }
            if kwargs.get("project_id"):
                data["project_id"] = kwargs["project_id"]

            for session in get_user_session(db_url=user_db_url):
                # 3. Find or Create Logic
                if entry_type_str in ["daily", "weekly", "monthly", "yearly"]:
                    existing = prod_service.list_journals(
                        session, entry_type=entry_type_enum, reference_date=ref_date,
                    )
                    if existing:
                        return ToolResult(
                            status="error",
                            tool_response=f"A {entry_type_str} journal for {ref_date_str} already exists (ID: {existing[0].id}). Use `read_journal` or `update_journal` instead.",
                        )

                # 4. Create it
                journal = prod_service.create_journal(session, data)
                journal_id = journal.id

            if journal_id is None:
                return ToolResult(status="error", tool_response="Failed to generate Journal ID.")

            entity = TrackedEntity(item_type="journal", item_id=journal_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"{entry_type_str.capitalize()} Journal created successfully with ID {journal_id}. It is pinned to your CLIPBOARD.",
                entities_to_track=[entity],
            )

        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date parsing error: {e!s}")
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to create journal: {e!s}")


# --- UPDATE TOOLS ---


class UpdateTasksTool(BaseTool):
    name = "update_tasks"
    description = (
        "Updates one or more tasks. You can use this to mark tasks as completed, change their deadlines, or reschedule them. "
        "Supports BULK updates by providing multiple task IDs. "
        "To CLEAR a date or description (e.g., removing a deadline), pass an empty string ''."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of task IDs to update.",
            },
            "status": {"type": "string", "description": "'todo', 'in_progress', 'completed', 'backlog'."},
            "title": {
                "type": "string",
                "description": "New title (Note: applies to ALL provided task_ids).",
            },
            "description": {"type": "string", "description": "New description. Pass '' to clear."},
            "assigned_date": {"type": "string", "description": "YYYY-MM-DD. Pass '' to clear."},
            "hard_deadline": {"type": "string", "description": "YYYY-MM-DD or ISO8601. Pass '' to clear."},
            "scheduled_start": {
                "type": "string",
                "description": "YYYY-MM-DD or ISO8601. Pass '' to clear.",
            },
            "add_project_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Project IDs to link these tasks to.",
            },
            "remove_project_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Project IDs to unlink from these tasks.",
            },
        },
        "required": ["task_ids"],
    }

    async def run(self, user_db_url: str | None = None, timezone: str = "UTC", **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        task_ids: list[int] = kwargs.get("task_ids", [])
        if not task_ids:
            return ToolResult(status="error", tool_response="No task_ids provided.")

        field_updates: dict[str, Any] = {}

        # 1. Standard Fields
        if "status" in kwargs:
            field_updates["status"] = kwargs["status"]
        if "title" in kwargs:
            field_updates["title"] = kwargs["title"]
        if "description" in kwargs:
            field_updates["description"] = None if kwargs["description"] == "" else kwargs["description"]

        # 2. Date Fields (Handling empty strings as 'clear')
        try:
            if "assigned_date" in kwargs:
                val = kwargs["assigned_date"]
                field_updates["assigned_date"] = None if val == "" else date.fromisoformat(val[:10])

            if "hard_deadline" in kwargs:
                val = kwargs["hard_deadline"]
                field_updates["hard_deadline"] = (
                    None if val == "" else _parse_to_utc(val, is_end_of_day=True, local_tz=timezone)
                )

            if "scheduled_start" in kwargs:
                val = kwargs["scheduled_start"]
                field_updates["scheduled_start"] = (
                    None if val == "" else _parse_to_utc(val, is_end_of_day=False, local_tz=timezone)
                )
        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date parsing error: {e!s}")

        add_project_ids = kwargs.get("add_project_ids")
        remove_project_ids = kwargs.get("remove_project_ids")

        if not field_updates and not add_project_ids and not remove_project_ids:
            return ToolResult(status="error", tool_response="No update fields provided.")

        try:
            updated_count = 0
            for session in get_user_session(db_url=user_db_url):
                updated_count = prod_service.bulk_update_tasks(
                    session=session,
                    task_ids=task_ids,
                    field_updates=field_updates,
                    add_project_ids=add_project_ids,
                    remove_project_ids=remove_project_ids,
                )

            if updated_count == 0:
                return ToolResult(
                    status="error", tool_response="No tasks were updated. Check if the task_ids exist.",
                )

            # Dynamic resolution: If they update just 1 task, show full detail. If bulk, show summary.
            res: Literal["detail", "summary"] = "detail" if len(task_ids) == 1 else "summary"
            entities = [
                TrackedEntity(item_type="task", item_id=t_id, resolution=res, ttl=10) for t_id in task_ids
            ]

            return ToolResult(
                status="success",
                tool_response=f"Successfully updated {updated_count} tasks. They have been pinned to your CLIPBOARD so you can verify the changes.",
                entities_to_track=entities,
            )

        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to update tasks: {e!s}")


class UpdateProjectTool(BaseTool):
    name = "update_project"
    description = "Updates an existing project. Pass an empty string '' to clear optional fields like description or deadline."
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "integer", "description": "ID of the project to update."},
            "name": {"type": "string", "description": "New name for the project."},
            "description": {"type": "string", "description": "New description. Pass '' to clear."},
            "status": {"type": "string", "description": "'todo', 'in_progress', 'completed', 'canceled'."},
            "start_date": {"type": "string", "description": "YYYY-MM-DD. Pass '' to clear."},
            "deadline": {"type": "string", "description": "YYYY-MM-DD. Pass '' to clear."},
        },
        "required": ["project_id"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(status="error", tool_response="project_id is required.")

        field_updates: dict[str, Any] = {}

        if "name" in kwargs:
            field_updates["name"] = kwargs["name"]
        if "status" in kwargs:
            field_updates["status"] = kwargs["status"]
        if "description" in kwargs:
            field_updates["description"] = None if kwargs["description"] == "" else kwargs["description"]

        try:
            if "start_date" in kwargs:
                val = kwargs["start_date"]
                field_updates["start_date"] = None if val == "" else date.fromisoformat(val[:10])

            if "deadline" in kwargs:
                val = kwargs["deadline"]
                field_updates["deadline"] = None if val == "" else date.fromisoformat(val[:10])
        except ValueError as e:
            return ToolResult(status="error", tool_response=f"Date parsing error: {e!s}")

        if not field_updates:
            return ToolResult(status="error", tool_response="No update fields provided.")

        try:
            was_updated = False
            for session in get_user_session(db_url=user_db_url):
                project = prod_service.update_project(session, project_id, field_updates)
                if project is not None:
                    was_updated = True

            if not was_updated:
                return ToolResult(status="error", tool_response=f"Project {project_id} not found.")

            entity = TrackedEntity(item_type="project", item_id=project_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Project {project_id} updated successfully. Pinned to CLIPBOARD.",
                entities_to_track=[entity],
            )

        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to update project: {e!s}")


class EditJournalTool(BaseTool):
    name = "edit_journal"
    description = (
        "Replaces a single specific block of text in a journal entry with new text. "
        "Use this tool to add, append, or replace the Markdown content of an existing journal. "
        "NOTE: You cannot change the entry_type or reference_date of a journal. "
        "After a successful edit, the updated journal will be pinned to your CLIPBOARD so you can verify the changes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "journal_id": {
                "type": "integer",
                "description": "The ID of the journal you want to edit.",
            },
            "old_str": {
                "type": "string",
                "description": "The exact block of text you want to replace. It must match the journal content EXACTLY, including indentation and line breaks.",
            },
            "new_str": {
                "type": "string",
                "description": "The new text that will replace 'old_str'.",
            },
            "title": {
                "type": "string",
                "description": "Optional. A new title for the journal entry.",
            },
            "project_id": {
                "type": "integer",
                "description": "Optional. The ID of a project to link this journal to.",
            },
        },
        "required": ["journal_id", "old_str", "new_str"],
    }

    async def run(self, user_db_url: str | None = None, **kwargs: Any) -> ToolResult:
        if not user_db_url:
            return ToolResult(status="error", tool_response="Database connection not available.")

        journal_id = kwargs.get("journal_id")
        old_str = kwargs.get("old_str")
        new_str = kwargs.get("new_str")

        if journal_id is None or old_str is None or new_str is None:
            return ToolResult(
                status="error", tool_response="Missing required fields (journal_id, old_str, new_str).",
            )

        try:
            was_updated = False
            for session in get_user_session(db_url=user_db_url):
                # 1. Fetch current journal
                journal = prod_service.get_journal(session, journal_id)
                if not journal:
                    return ToolResult(status="error", tool_response=f"Journal ID {journal_id} not found.")

                current_content = journal.content

                # 2. Safety check: Exact match logic
                occurrence_count = current_content.count(old_str)

                if occurrence_count == 0:
                    return ToolResult(
                        status="error",
                        tool_response=(
                            f"Could not find the old string you specified.\n"
                            f"Please read the journal content (ID: {journal_id}) from your clipboard "
                            "and ensure your 'old_str' matches the characters and line breaks exactly. "
                            "Using a smaller 'old_str' might help."
                        ),
                    )

                if occurrence_count > 1:
                    return ToolResult(
                        status="error",
                        tool_response=(
                            f"Found {occurrence_count} occurrences of your old string in Journal {journal_id}. "
                            "Please include more surrounding lines in 'old_str' to make the match unique."
                        ),
                    )

                # 3. Perform the replacement
                new_content = current_content.replace(old_str, new_str)

                # 4. Prepare update payload
                update_data: dict[str, Any] = {"content": new_content}
                if "title" in kwargs:
                    update_data["title"] = kwargs["title"]
                if "project_id" in kwargs:
                    update_data["project_id"] = kwargs["project_id"]

                # 5. Commit update
                updated_journal = prod_service.update_journal(session, journal_id, update_data)
                if updated_journal:
                    was_updated = True

            if not was_updated:
                return ToolResult(status="error", tool_response=f"Failed to update Journal {journal_id}.")

            # 6. Signal the Agent Loop to pin the updated journal to the clipboard
            entity = TrackedEntity(item_type="journal", item_id=journal_id, resolution="detail", ttl=10)
            return ToolResult(
                status="success",
                tool_response=f"Journal {journal_id} edited successfully! The updated content is now pinned to your CLIPBOARD. Please verify the changes.",
                entities_to_track=[entity],
            )

        except Exception as e:
            return ToolResult(status="error", tool_response=f"Failed to edit journal: {e!s}")
