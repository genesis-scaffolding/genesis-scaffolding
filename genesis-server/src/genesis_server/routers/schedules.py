from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..database import get_session
from ..dependencies import get_current_active_user, get_scheduler_manager, get_user_inbox_path
from ..models.user import User
from ..models.workflow_schedule import WorkflowSchedule
from ..scheduler import SchedulerManager
from ..schemas.workflow_schedule import WorkflowScheduleCreate, WorkflowScheduleRead, WorkflowScheduleUpdate

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/", response_model=WorkflowScheduleRead)
async def create_schedule(
    payload: WorkflowScheduleCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    user_inbox: Annotated[Path, Depends(get_user_inbox_path)],
    session: Annotated[Session, Depends(get_session)],
    scheduler: Annotated[SchedulerManager, Depends(get_scheduler_manager)],
):
    # 1. Capture the directory from the dependency
    db_schedule = WorkflowSchedule(
        **payload.model_dump(), user_id=cast("int", user.id), user_directory=str(user_inbox),
    )

    session.add(db_schedule)
    session.commit()
    session.refresh(db_schedule)

    # 2. Add to the running scheduler if enabled
    if db_schedule.enabled:
        scheduler.upsert_schedule(db_schedule)

    return db_schedule


@router.get("/", response_model=list[WorkflowScheduleRead])
async def list_schedules(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
):
    statement = select(WorkflowSchedule).where(WorkflowSchedule.user_id == user.id)
    return session.exec(statement).all()


@router.get("/{schedule_id}", response_model=WorkflowScheduleRead)
async def get_schedule(
    schedule_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
):
    schedule = session.get(WorkflowSchedule, schedule_id)
    if not schedule or schedule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.patch("/{schedule_id}", response_model=WorkflowScheduleRead)
async def update_schedule(
    schedule_id: int,
    payload: WorkflowScheduleUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    scheduler: Annotated[SchedulerManager, Depends(get_scheduler_manager)],
):
    db_schedule = session.get(WorkflowSchedule, schedule_id)
    if not db_schedule or db_schedule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_schedule, key, value)

    session.add(db_schedule)
    session.commit()
    session.refresh(db_schedule)

    # Sync with the background scheduler
    if db_schedule.enabled:
        scheduler.upsert_schedule(db_schedule)
    else:
        scheduler.remove_schedule(cast("int", db_schedule.id))

    return db_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    scheduler: Annotated[SchedulerManager, Depends(get_scheduler_manager)],
):
    db_schedule = session.get(WorkflowSchedule, schedule_id)
    if not db_schedule or db_schedule.user_id != user.id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from memory first
    scheduler.remove_schedule(cast("int", db_schedule.id))

    # Remove from DB
    session.delete(db_schedule)
    session.commit()
