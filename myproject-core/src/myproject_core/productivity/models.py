from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import MetaData
from sqlmodel import Field, Relationship, SQLModel

# 1. Define a dedicated metadata for productivity models to avoid collision
# with the system-wide metadata used in myproject_server.
productivity_metadata = MetaData()


class JournalType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    PROJECT = "project"


class Status(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"


def get_utc_now():
    """Helper to handle the deprecated utcnow()"""
    return datetime.now(timezone.utc)


class ProjectTaskLink(SQLModel, table=True):
    metadata = productivity_metadata
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id", primary_key=True)


class Project(SQLModel, table=True):
    metadata = productivity_metadata
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    start_date: Optional[date] = None
    deadline: Optional[date] = None
    status: Status = Field(default=Status.TODO)

    # Relationships
    tasks: list["Task"] = Relationship(back_populates="projects", link_model=ProjectTaskLink)
    journals: list["JournalEntry"] = Relationship(back_populates="project")


class Task(SQLModel, table=True):
    metadata = productivity_metadata
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None

    # Timing Logic
    hard_deadline: Optional[datetime] = None  # The "Boss" deadline
    assigned_date: Optional[date] = None  # "I want to do this Friday"

    # Appointment Logic
    start_time: Optional[time] = None  # Specific time of day
    duration_minutes: Optional[int] = None  # For calendar blocking

    status: Status = Field(default=Status.TODO)
    created_at: datetime = Field(default_factory=get_utc_now)
    completed_at: Optional[datetime] = None

    # Relationships
    projects: list[Project] = Relationship(back_populates="tasks", link_model=ProjectTaskLink)

    # Helper to easily get project ids related to a task from database
    @property
    def project_ids(self) -> list[int]:
        return [p.id for p in self.projects if p.id is not None]


class JournalEntry(SQLModel, table=True):
    metadata = productivity_metadata
    id: Optional[int] = Field(default=None, primary_key=True)
    entry_type: JournalType = Field(index=True)

    # The date this entry refers to:
    # - For Daily: The specific day
    # - For Weekly: The Monday of that week
    # - For Monthly: The 1st of the month
    reference_date: date = Field(index=True)

    title: Optional[str] = None
    content: str  # Markdown text for goals, reviews, logs

    # Optional link to a project (for project-specific logs)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    project: Optional[Project] = Relationship(back_populates="journals")

    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
