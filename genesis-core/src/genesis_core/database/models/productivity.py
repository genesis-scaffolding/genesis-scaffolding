from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, MetaData
from sqlmodel import Field, Relationship, SQLModel

# 1. Define a dedicated metadata for productivity models to avoid collision
# with the system-wide metadata used in genesis_server.
productivity_metadata = MetaData()


class JournalType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    PROJECT = "project"
    GENERAL = "general"


class Status(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"


def get_utc_now():
    """Helper to handle the deprecated utcnow()"""
    return datetime.now(UTC)


class ProjectTaskLink(SQLModel, table=True):
    metadata = productivity_metadata
    project_id: int | None = Field(default=None, foreign_key="project.id", primary_key=True)
    task_id: int | None = Field(default=None, foreign_key="task.id", primary_key=True)


class Project(SQLModel, table=True):
    metadata = productivity_metadata
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None

    start_date: date | None = None
    deadline: date | None = None
    status: Status = Field(default=Status.TODO)

    # Relationships
    tasks: list["Task"] = Relationship(back_populates="projects", link_model=ProjectTaskLink)
    journals: list["JournalEntry"] = Relationship(back_populates="project")


class Task(SQLModel, table=True):
    metadata = productivity_metadata
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: str | None = None

    # --- ABSOLUTE TIME (UTC) ---
    # We use sa_column to force SQLModel/SQLAlchemy to treat these as
    # Timezone-aware. SQLite will store these as ISO strings.
    created_at: datetime = Field(
        default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    # The "Boss" deadline. If it's 5pm, it's 5pm in a specific TZ.
    hard_deadline: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # --- FLOATING TIME (Calendar Dates) ---
    # They represent "The day the user sees on their wall calendar."
    assigned_date: date | None = None

    # --- APPOINTMENT (Absolute UTC) ---
    # User says: "Dentist at 9:00 AM Adelaide time."
    # The Frontend converts "9:00 AM Friday Adelaide" -> "11:30 PM Thursday UTC"
    # We store the UTC version here.
    scheduled_start: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    duration_minutes: int | None = None

    status: Status = Field(default=Status.TODO)

    # Relationships
    projects: list[Project] = Relationship(back_populates="tasks", link_model=ProjectTaskLink)

    # Helper to easily get project ids related to a task from database
    @property
    def project_ids(self) -> list[int]:
        return [p.id for p in self.projects if p.id is not None]


class JournalEntry(SQLModel, table=True):
    metadata = productivity_metadata
    id: int | None = Field(default=None, primary_key=True)
    entry_type: JournalType = Field(index=True)

    title: str | None = None
    content: str  # Markdown text for goals, reviews, logs

    # Optional link to a project (for project-specific logs)
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: Project | None = Relationship(back_populates="journals")

    # The date this entry refers to:
    # - For Daily: The specific day
    # - For Weekly: The Monday of that week
    # - For Monthly: The 1st of the month
    reference_date: date = Field(index=True)

    created_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))

    updated_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
