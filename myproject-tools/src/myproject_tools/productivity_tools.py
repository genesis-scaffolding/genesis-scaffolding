import zoneinfo
from datetime import date, datetime, time, timezone
from typing import Any

from myproject_core.productivity.db import get_user_session
from myproject_core.productivity.models import JournalEntry, Project, ProjectTaskLink, Task
from sqlmodel import and_, col, or_, select

from .base import BaseTool
from .schema import ToolResult, TrackedEntity


def _parse_to_utc(date_str: str, is_end_of_day: bool, local_tz: str) -> datetime:
    """
    Helper to convert agent date/time strings into UTC datetimes for database querying.
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
        return local_dt.astimezone(timezone.utc)

    # If it's a full ISO timestamp
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        # Assume it was provided in the local timezone if naive
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


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
                col(ProjectTaskLink.project_id) == kwargs.get("project_id")
            )

        # 2. DYNAMIC FILTERS (Combined via query_logic)
        dynamic_conditions = []

        # Text Search
        search_query = kwargs.get("search_query")
        if search_query:
            search_pattern = f"%{search_query}%"
            dynamic_conditions.append(
                or_(col(Task.title).like(search_pattern), col(Task.description).like(search_pattern))
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
            return ToolResult(status="error", tool_response=f"Date parsing error: {str(e)}")
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Search failed: {str(e)}")


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
            }
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
            return ToolResult(status="error", tool_response=f"Failed to read task: {str(e)}")


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
                or_(col(Project.name).like(search_pattern), col(Project.description).like(search_pattern))
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
                col(Project.status).desc(), col(Project.deadline).asc(), col(Project.name).asc()
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
            return ToolResult(status="error", tool_response=f"Search failed: {str(e)}")


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
            return ToolResult(status="error", tool_response=f"Failed to read project: {str(e)}")


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
                )
            )

        ref_date_start = kwargs.get("reference_date_start")
        ref_date_end = kwargs.get("reference_date_end")

        # Group the date range together
        date_conditions = []
        if ref_date_start:
            date_conditions.append(
                col(JournalEntry.reference_date) >= date.fromisoformat(ref_date_start[:10])
            )
        if ref_date_end:
            date_conditions.append(
                col(JournalEntry.reference_date) <= date.fromisoformat(ref_date_end[:10])
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
            return ToolResult(status="error", tool_response=f"Search failed: {str(e)}")


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
            return ToolResult(status="error", tool_response=f"Failed to read journal: {str(e)}")
