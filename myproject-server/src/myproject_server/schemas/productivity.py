from datetime import date, datetime, time, timezone
from typing import Annotated, Optional

from myproject_core.productivity.models import JournalType, Status
from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer

# --- Utilities ---


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Validator to ensure that any incoming datetime is converted to UTC
    and remains timezone-aware.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If the frontend forgot to send a timezone, we assume UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def serialize_utc(dt: datetime) -> str:
    """Output: Ensures outgoing datetimes have the 'Z' suffix and 3ms decimals."""
    if dt is None:
        return None
    # Ensure it's treated as UTC even if the DB returned it as naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Format: 2024-10-25T14:30:00.000Z
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Type alias for cleaner code
UtcDatetime = Annotated[
    datetime, AfterValidator(ensure_utc), PlainSerializer(serialize_utc, when_used="json")
]


class ProductivityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Task Schemas ---
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    # Absolute Point in Time (UTC)
    hard_deadline: Optional[UtcDatetime] = None

    # The Intent/Planning Day (Floating Date)
    assigned_date: Optional[date] = None

    # The Appointment (Calendar Block - Absolute UTC)
    scheduled_start: Optional[UtcDatetime] = None
    duration_minutes: Optional[int] = None

    status: Status = Status.TODO
    project_ids: Optional[list[int]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hard_deadline: Optional[UtcDatetime] = None
    assigned_date: Optional[date] = None
    scheduled_start: Optional[UtcDatetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[Status] = None
    completed_at: Optional[UtcDatetime] = None


class TaskRead(ProductivityBase):
    id: int
    title: str
    description: Optional[str]
    hard_deadline: Optional[UtcDatetime]
    assigned_date: Optional[date]
    scheduled_start: Optional[UtcDatetime]
    duration_minutes: Optional[int]
    status: Status
    created_at: UtcDatetime
    completed_at: Optional[UtcDatetime]
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
    project_id: Optional[int] = None


class JournalEntryRead(JournalEntryCreate, ProductivityBase):
    id: int
    created_at: UtcDatetime
    updated_at: UtcDatetime
