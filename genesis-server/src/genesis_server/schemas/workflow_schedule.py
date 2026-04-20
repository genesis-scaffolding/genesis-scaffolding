from datetime import datetime
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field, field_validator


class WorkflowScheduleCreate(BaseModel):
    name: str = Field(..., description="A friendly name for this schedule")
    workflow_id: str = Field(..., description="The ID of the workflow to run")
    cron_expression: str = Field(..., description="Standard crontab expression (e.g. '0 9 * * *')")
    timezone: str = Field(default="UTC", description="IANA Timezone string")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Inputs for the workflow")
    enabled: bool = True

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        try:
            CronTrigger.from_crontab(v)
        except Exception as exc:
            raise ValueError("Invalid cron expression format") from exc
        return v


class WorkflowScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    inputs: dict[str, Any] | None = None
    enabled: bool | None = None


class WorkflowScheduleRead(WorkflowScheduleCreate):
    id: int
    user_id: int
    last_run_at: datetime | None = None
