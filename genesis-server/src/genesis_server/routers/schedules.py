
from fastapi import APIRouter, HTTPException, status

from genesis_server.dependencies import CoreDep, InboxDep
from genesis_server.schemas.workflow_schedule import (
    WorkflowScheduleCreate,
    WorkflowScheduleRead,
    WorkflowScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=WorkflowScheduleRead)
async def create_schedule(
    payload: WorkflowScheduleCreate,
    core: CoreDep,
    user_inbox: InboxDep,
):
    """Create a new scheduled workflow."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    schedule = core.scheduled_job_manager.create_schedule(
        user_id=user_id,
        name=payload.name,
        workflow_id=payload.workflow_id,
        cron_expression=payload.cron_expression,
        inputs=payload.inputs,
        user_directory=str(user_inbox),
        timezone=payload.timezone,
        enabled=payload.enabled,
    )

    # Add to the running scheduler if enabled
    if schedule.enabled:
        core.scheduler.upsert_schedule(schedule)

    return schedule


@router.get("/", response_model=list[WorkflowScheduleRead])
async def list_schedules(core: CoreDep):
    """List all scheduled workflows for the current user."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")
    return core.scheduled_job_manager.list_schedules(user_id)


@router.get("/{schedule_id}", response_model=WorkflowScheduleRead)
async def get_schedule(
    schedule_id: int,
    core: CoreDep,
):
    """Get a specific schedule by ID."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    schedule = core.scheduled_job_manager.get_schedule(schedule_id, user_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.patch("/{schedule_id}", response_model=WorkflowScheduleRead)
async def update_schedule(
    schedule_id: int,
    payload: WorkflowScheduleUpdate,
    core: CoreDep,
):
    """Update a scheduled workflow."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    data = payload.model_dump(exclude_unset=True)
    schedule = core.scheduled_job_manager.update_schedule(schedule_id, user_id, **data)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Sync with the background scheduler
    if schedule.enabled:
        core.scheduler.upsert_schedule(schedule)
    else:
        core.scheduler.remove_schedule(schedule_id)

    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    core: CoreDep,
):
    """Delete a scheduled workflow."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    # Remove from scheduler first
    core.scheduler.remove_schedule(schedule_id)

    # Remove from DB
    result = core.scheduled_job_manager.delete_schedule(schedule_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
