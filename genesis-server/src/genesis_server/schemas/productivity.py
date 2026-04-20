from datetime import UTC, date, datetime
from typing import Annotated

from genesis_core.productivity.models import JournalType, Status
from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer

# --- Utilities ---


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Validator to ensure that any incoming datetime is converted to UTC
    and remains timezone-aware.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If the frontend forgot to send a timezone, we assume UTC
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def serialize_utc(dt: datetime) -> str:
    """Output: Ensures outgoing datetimes have the 'Z' suffix and 3ms decimals."""
    if dt is None:
        return None
    # Ensure it's treated as UTC even if the DB returned it as naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    # Format: 2024-10-25T14:30:00.000Z
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Type alias for cleaner code
UtcDatetime = Annotated[
    datetime, AfterValidator(ensure_utc), PlainSerializer(serialize_utc, when_used="json"),
]


class ProductivityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Task Schemas ---
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    # Absolute Point in Time (UTC)
    hard_deadline: UtcDatetime | None = None

    # The Intent/Planning Day (Floating Date)
    assigned_date: date | None = None

    # The Appointment (Calendar Block - Absolute UTC)
    scheduled_start: UtcDatetime | None = None
    duration_minutes: int | None = None

    status: Status = Status.TODO
    project_ids: list[int] | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    hard_deadline: UtcDatetime | None = None
    assigned_date: date | None = None
    scheduled_start: UtcDatetime | None = None
    duration_minutes: int | None = None
    status: Status | None = None
    completed_at: UtcDatetime | None = None


class TaskRead(ProductivityBase):
    id: int
    title: str
    description: str | None
    hard_deadline: UtcDatetime | None
    assigned_date: date | None
    scheduled_start: UtcDatetime | None
    duration_minutes: int | None
    status: Status
    created_at: UtcDatetime
    completed_at: UtcDatetime | None
    project_ids: list[int] = []


class TaskBulkUpdate(BaseModel):
    ids: list[int]
    updates: TaskUpdate
    # Optional: If provided, these projects will be ADDED to all selected tasks
    add_project_ids: list[int] | None = None
    # Optional: If provided, these projects will be REMOVED from all selected tasks
    remove_project_ids: list[int] | None = None
    # Optional: If provided, replaces all existing project links with these ones
    set_project_ids: list[int] | None = None


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    status: Status = Status.TODO


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    status: Status | None = None


class ProjectRead(ProjectCreate, ProductivityBase):
    id: int


# --- Journal Schemas ---
class JournalEntryCreate(BaseModel):
    entry_type: JournalType
    reference_date: date
    title: str | None = None
    content: str
    project_id: int | None = None


class JournalEntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    reference_date: date | None = None
    project_id: int | None = None


class JournalEntryRead(JournalEntryCreate, ProductivityBase):
    id: int
    created_at: UtcDatetime
    updated_at: UtcDatetime
