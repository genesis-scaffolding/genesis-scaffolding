"""
Scheduled workflow subsystem manager for genesis_core.

Wraps the system database and provides CRUD operations for WorkflowSchedule.
"""

from typing import Any

from sqlmodel import col, select

from ..configs import Config
from ..database import get_session_context
from ..database.models import WorkflowSchedule


class ScheduledJobManager:
    """Manager for scheduled workflows (system DB)."""

    def __init__(self, config: Config):
        self.config = config

    def list_schedules(self, user_id: int) -> list[WorkflowSchedule]:
        """List all schedules for a user."""
        with get_session_context() as session:
            return list(
                session.exec(
                    select(WorkflowSchedule)
                    .where(WorkflowSchedule.user_id == user_id)
                    .order_by(col(WorkflowSchedule.name).asc())
                ).all()
            )

    def list_enabled_schedules(self) -> list[WorkflowSchedule]:
        """List all enabled schedules (used by scheduler at startup)."""
        with get_session_context() as session:
            return list(
                session.exec(
                    select(WorkflowSchedule).where(WorkflowSchedule.enabled).all()
                )
            )

    def get_schedule_by_id(self, schedule_id: int) -> WorkflowSchedule | None:
        """Get a schedule by ID without user filter (used by scheduler)."""
        with get_session_context() as session:
            return session.get(WorkflowSchedule, schedule_id)

    def update_last_run(self, schedule_id: int) -> None:
        """Update last_run_at timestamp."""
        with get_session_context() as session:
            schedule = session.get(WorkflowSchedule, schedule_id)
            if schedule:
                from datetime import UTC, datetime
                schedule.last_run_at = datetime.now(UTC)
                session.add(schedule)
                session.commit()

    def get_schedule(self, schedule_id: int, user_id: int) -> WorkflowSchedule | None:
        """Get a schedule by ID."""
        with get_session_context() as session:
            schedule = session.get(WorkflowSchedule, schedule_id)
            if not schedule or schedule.user_id != user_id:
                return None
            return schedule

    def create_schedule(
        self,
        user_id: int,
        name: str,
        workflow_id: str,
        cron_expression: str,
        inputs: dict[str, Any],
        user_directory: str,
        timezone: str = "UTC",
        enabled: bool = True,
    ) -> WorkflowSchedule:
        """Create a new schedule."""
        with get_session_context() as session:
            schedule = WorkflowSchedule(
                user_id=user_id,
                name=name,
                workflow_id=workflow_id,
                cron_expression=cron_expression,
                timezone=timezone,
                inputs=inputs,
                user_directory=user_directory,
                enabled=enabled,
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            return schedule

    def update_schedule(
        self, schedule_id: int, user_id: int, **kwargs
    ) -> WorkflowSchedule | None:
        """Update schedule fields."""
        with get_session_context() as session:
            schedule = session.get(WorkflowSchedule, schedule_id)
            if not schedule or schedule.user_id != user_id:
                return None
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            return schedule

    def delete_schedule(self, schedule_id: int, user_id: int) -> bool:
        """Delete a schedule."""
        with get_session_context() as session:
            schedule = session.get(WorkflowSchedule, schedule_id)
            if not schedule or schedule.user_id != user_id:
                return False
            session.delete(schedule)
            session.commit()
            return True

    def set_enabled(self, schedule_id: int, user_id: int, enabled: bool) -> WorkflowSchedule | None:
        """Enable or disable a schedule."""
        return self.update_schedule(schedule_id, user_id, enabled=enabled)
