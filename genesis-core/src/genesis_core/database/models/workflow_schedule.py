from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User
    from .workflow_job import WorkflowJob


class WorkflowScheduleBase(SQLModel):
    name: str = Field(index=True)
    workflow_id: str = Field(index=True)  # ID from the YAML manifest
    cron_expression: str  # e.g., "0 9 * * *"
    timezone: str = Field(default="UTC")  # IANA string e.g., "Australia/Adelaide"

    # The static inputs to be passed to the workflow every time it runs
    inputs: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Store the absolute path provided by the 'get_user_inbox_path' dependency
    user_directory: str

    enabled: bool = Field(default=True, index=True)
    last_run_at: datetime | None = None


class WorkflowSchedule(WorkflowScheduleBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id", index=True)
    user: "User" = Relationship()

    # Link to all jobs spawned by this schedule
    jobs: list["WorkflowJob"] = Relationship(back_populates="schedule")
