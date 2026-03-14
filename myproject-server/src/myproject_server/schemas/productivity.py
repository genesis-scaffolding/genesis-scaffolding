from datetime import date, datetime, time
from typing import Optional

from myproject_core.productivity.models import JournalType, Status
from pydantic import BaseModel, ConfigDict


class ProductivityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Task Schemas ---
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    hard_deadline: Optional[datetime] = None
    assigned_date: Optional[date] = None
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    status: Status = Status.TODO
    # Efficiency fix: Allow linking projects during creation
    project_ids: Optional[list[int]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hard_deadline: Optional[datetime] = None
    assigned_date: Optional[date] = None
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    status: Optional[Status] = None
    completed_at: Optional[datetime] = None


class TaskRead(ProductivityBase):
    id: int
    title: str
    description: Optional[str]
    hard_deadline: Optional[datetime]
    assigned_date: Optional[date]
    start_time: Optional[time]
    duration_minutes: Optional[int]
    status: Status
    created_at: datetime
    completed_at: Optional[datetime]
    project_ids: list[int] = []


class TaskBulkUpdate(BaseModel):
    ids: list[int]
    updates: TaskUpdate
    # Optional: If provided, these projects will be ADDED to all selected tasks
    add_project_ids: Optional[list[int]] = None
    # Optional: If provided, these projects will be REMOVED from all selected tasks
    remove_project_ids: Optional[list[int]] = None
    # Optional: If provided, replaces all existing project links with these ones
    set_project_ids: Optional[list[int]] = None


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    status: Status = Status.TODO


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    status: Optional[Status] = None


class ProjectRead(ProjectCreate, ProductivityBase):
    id: int


# --- Journal Schemas ---
class JournalEntryCreate(BaseModel):
    entry_type: JournalType
    reference_date: date
    title: Optional[str] = None
    content: str
    project_id: Optional[int] = None


class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    reference_date: Optional[date] = None


class JournalEntryRead(JournalEntryCreate, ProductivityBase):
    id: int
    created_at: datetime
    updated_at: datetime
