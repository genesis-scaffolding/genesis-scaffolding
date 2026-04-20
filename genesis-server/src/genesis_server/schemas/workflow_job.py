from datetime import datetime
from typing import Any

from genesis_core.configs import settings
from pydantic import BaseModel, ConfigDict, model_validator

from ..models.workflow_job import JobStatus


class WorkflowJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: str
    status: JobStatus
    inputs: dict
    result: dict | None
    step_status: dict[str, str]
    error_message: str | None
    workspace_path: str | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def sanitize_internal_paths(self) -> "WorkflowJobRead":
        # The prefix we want to hide
        root_prefix = str(settings.path.inbox_directory.resolve())

        def _clean(val: Any) -> Any:
            if isinstance(val, str):
                # Replace absolute path with a relative placeholder
                return val.replace(root_prefix, "[SANDBOX]")
            if isinstance(val, dict):
                return {k: _clean(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_clean(i) for i in val]
            return val

        self.inputs = _clean(self.inputs)
        if self.error_message:
            self.error_message = _clean(self.error_message)

        # Never show the raw workspace_path to the frontend
        self.workspace_path = None
        return self


class WorkflowRunResponse(BaseModel):
    message: str
    job_id: int
