"""
Workflow job subsystem manager for genesis_core.

Wraps the system database and provides CRUD operations for WorkflowJob.
"""

from datetime import UTC, datetime
from typing import Any

from sqlmodel import col, select

from ..configs import Config
from ..database import get_session_context
from ..database.models import JobStatus, WorkflowJob


class WorkflowJobManager:
    """Manager for workflow jobs (system DB)."""

    def __init__(self, config: Config):
        self.config = config

    def list_jobs(
        self,
        user_id: int,
        workflow_id: str | None = None,
        status: JobStatus | None = None,
        schedule_id: int | None = None,
    ) -> list[WorkflowJob]:
        """List workflow jobs for a user, optionally filtered."""
        with get_session_context() as session:
            statement = (
                select(WorkflowJob)
                .where(WorkflowJob.user_id == user_id)
                .order_by(col(WorkflowJob.created_at).desc())
            )
            if workflow_id:
                statement = statement.where(WorkflowJob.workflow_id == workflow_id)
            if status:
                statement = statement.where(WorkflowJob.status == status)
            if schedule_id:
                statement = statement.where(WorkflowJob.schedule_id == schedule_id)
            return list(session.exec(statement).all())

    def get_job(self, job_id: int, user_id: int) -> WorkflowJob | None:
        """Get a workflow job by ID."""
        with get_session_context() as session:
            job = session.get(WorkflowJob, job_id)
            if not job or job.user_id != user_id:
                return None
            return job

    def create_job(
        self,
        user_id: int,
        workflow_id: str,
        inputs: dict[str, Any],
        schedule_id: int | None = None,
    ) -> WorkflowJob:
        """Create a new workflow job."""
        with get_session_context() as session:
            job = WorkflowJob(
                workflow_id=workflow_id,
                user_id=user_id,
                inputs=inputs,
                status=JobStatus.PENDING,
                schedule_id=schedule_id,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def update_job(self, job_id: int, user_id: int, **kwargs) -> WorkflowJob | None:
        """Update job fields."""
        with get_session_context() as session:
            job = session.get(WorkflowJob, job_id)
            if not job or job.user_id != user_id:
                return None
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def mark_running(self, job_id: int, user_id: int) -> WorkflowJob | None:
        """Mark a job as running."""
        return self.update_job(job_id, user_id, status=JobStatus.RUNNING)

    def mark_completed(self, job_id: int, user_id: int, result: dict[str, Any]) -> WorkflowJob | None:
        """Mark a job as completed with result."""
        return self.update_job(job_id, user_id, status=JobStatus.COMPLETED, result=result)

    def mark_failed(self, job_id: int, user_id: int, error_message: str) -> WorkflowJob | None:
        """Mark a job as failed with error message."""
        return self.update_job(
            job_id, user_id, status=JobStatus.FAILED, error_message=error_message,
        )

    def update_step_status(
        self,
        job_id: int,
        user_id: int,
        step_name: str,
        step_status: str,
    ) -> WorkflowJob | None:
        """Update the status of a specific step in a job."""
        with get_session_context() as session:
            job = session.get(WorkflowJob, job_id)
            if not job or job.user_id != user_id:
                return None
            step_status_dict = job.step_status or {}
            step_status_dict[step_name] = step_status
            job.step_status = step_status_dict
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
