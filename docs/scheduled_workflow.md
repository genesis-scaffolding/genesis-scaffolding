# Scheduled Workflow Architecture

## Overview

Scheduled workflows allow users to register a workflow to run automatically at cron-defined times. The system stores the schedule in the server database and uses APScheduler to fire the execution at the right time. When the time comes, the scheduler resolves the user's environment just-in-time and runs the workflow.

There are two distinct phases:

1. **Registration** — User creates a schedule via the REST API. The server stores it in the database and registers it with APScheduler.
2. **Execution** — When the cron expression fires, APScheduler calls the task function, which resolves the user's context, creates a job record, and runs the workflow.

## Phase 1: Schedule Registration

### API Endpoint

`POST /schedules/` accepts a `WorkflowScheduleCreate` payload:

```json
{
  "name": "Morning research digest",
  "workflow_id": "web-research",
  "cron_expression": "0 9 * * *",
  "timezone": "Australia/Adelaide",
  "inputs": { "topic": "machine learning", "max_results": 5 },
  "enabled": true
}
```

The `cron_expression` field is validated at the Pydantic level by attempting to parse it with `CronTrigger.from_crontab`. If the expression is malformed, the request is rejected before reaching the handler.

### Database Model

The `WorkflowSchedule` table stores the full schedule definition:

```python
# models/workflow_schedule.py
class WorkflowSchedule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    workflow_id: str          # ID from the workflow YAML manifest
    cron_expression: str      # e.g., "0 9 * * *"
    timezone: str            # IANA timezone string, e.g., "Australia/Adelaide"
    inputs: dict[str, Any]    # Static inputs applied every run
    user_directory: str      # Absolute path to the user's inbox directory
    enabled: bool = True
    last_run_at: datetime | None
```

`inputs` holds the workflow parameters that will be used every time the schedule fires. These are stored as a JSON blob at registration time.

### APScheduler Registration

When `create_schedule` saves the schedule to the database, it immediately calls `scheduler.upsert_schedule()` if `enabled` is `True`:

```python
# routers/schedules.py
@router.post("/", response_model=WorkflowScheduleRead)
async def create_schedule(
    payload: WorkflowScheduleCreate,
    user: User,
    user_inbox: Path,          # user's working directory
    session: Session,
    scheduler: SchedulerManager,
):
    db_schedule = WorkflowSchedule(
        **payload.model_dump(),
        user_id=user.id,
        user_directory=str(user_inbox),
    )
    session.add(db_schedule)
    session.commit()
    session.refresh(db_schedule)

    if db_schedule.enabled:
        scheduler.upsert_schedule(db_schedule)  # Register with APScheduler

    return db_schedule
```

`upsert_schedule` translates the cron expression into an APScheduler trigger and registers the background task:

```python
# scheduler.py
def upsert_schedule(self, schedule: WorkflowSchedule):
    job_id = f"sched_{schedule.id}"
    trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone=schedule.timezone)

    self.scheduler.add_job(
        self._execute_scheduled_task,
        trigger=trigger,
        id=job_id,
        args=[schedule.id, schedule.user_id],
        replace_existing=True,
    )
```

- The job ID format is `sched_{schedule.id}`, used for idempotent replacement on subsequent updates
- `args=[schedule.id, schedule.user_id]` means the scheduler only needs to store minimal data — it fetches the full schedule from the database at execution time
- `replace_existing=True` allows `upsert_schedule` to be called again on update without creating duplicate jobs

## Phase 2: Execution at Schedule Time

### Startup Sync

On server startup, `main.py` calls `await sm.sync_schedules()` to reload all enabled schedules from the database into APScheduler. This ensures no schedules are lost if the server restarts.

### Just-in-Time User Context Resolution

When APScheduler fires `_execute_scheduled_task`, it receives only `schedule_id` and `user_id`. The function resolves the full user context at execution time rather than at registration time:

```python
# scheduler.py
async def _execute_scheduled_task(self, schedule_id: int, user_id: int):
    with Session(db_engine) as session:
        schedule = session.get(WorkflowSchedule, schedule_id)
        user = session.get(User, user_id)
        if not schedule or not schedule.enabled or not user:
            return

        # Resolve user's working directory and config
        user_workdir = server_settings.path.server_users_directory / str(user.id)
        user_config = get_config(
            user_workdir=user_workdir,
            override_yaml=user_workdir / "config.yaml",
        )

        # Rebuild all user-scoped components fresh
        user_registry = WorkflowRegistry(user_config)
        user_agent_registry = AgentRegistry(user_config)
        user_wm = WorkspaceManager(user_config)
        user_engine = WorkflowEngine(user_wm, user_agent_registry, user_config.path.working_directory)
```

This pattern means the scheduler always uses the user's current configuration and registered workflows — even if the user updated their config or workflow definitions since the schedule was created.

### Job Creation and Execution

After resolving the user context, the task creates a job record and runs it:

```python
# scheduler.py
# 1. Get the workflow manifest
workflow_manifest = user_registry.get_workflow(schedule.workflow_id)
if not workflow_manifest:
    return

# 2. Create the job record (resolves relative file paths to the inbox)
job = await add_workflow_job(
    inputs=schedule.inputs,
    user_inbox=user_config.path.working_directory,
    user_id=user_id,
    workflow_id=schedule.workflow_id,
    manifest=workflow_manifest,
)

# 3. Run the workflow
await run_workflow_job(
    job_id=job.id,
    engine_instance=user_engine,
    registry_instance=user_registry,
)

# 4. Update schedule timestamp
job.schedule_id = schedule.id
schedule.last_run_at = datetime.now(UTC)
session.add(job)
session.add(schedule)
session.commit()
```

`add_workflow_job` writes a `WorkflowJob` record to the database, resolving relative file paths in the inputs against the user's inbox directory. `run_workflow_job` loads that record, executes the workflow via the user's engine, and updates the job status to `COMPLETED` or `FAILED`.

### Schedule Updates

When a user updates a schedule via `PATCH /schedules/{id}`:

```python
@router.patch("/{schedule_id}", ...)
async def update_schedule(...):
    db_schedule = session.get(...)
    # Apply field updates
    session.add(db_schedule)
    session.commit()

    # Sync APScheduler
    if db_schedule.enabled:
        scheduler.upsert_schedule(db_schedule)  # Replaces existing job with updated trigger
    else:
        scheduler.remove_schedule(db_schedule.id)
```

Calling `upsert_schedule` again with `replace_existing=True` replaces the existing APScheduler job with the new cron expression or timezone, without needing to delete and re-add.

### Schedule Deletion

When a user deletes a schedule via `DELETE /schedules/{id}`:

```python
@router.delete("/{schedule_id}", ...)
async def delete_schedule(...):
    scheduler.remove_schedule(db_schedule.id)  # Remove from APScheduler first
    session.delete(db_schedule)                  # Then remove from DB
    session.commit()
```

Removing from APScheduler before the database ensures no orphaned job fires after the record is deleted.

## Key Files

| File | Role |
|---|---|
| `genesis-server/src/genesis_server/routers/schedules.py` | CRUD endpoints for schedule management |
| `genesis-server/src/genesis_server/scheduler.py` | `SchedulerManager`, APScheduler registration, `_execute_scheduled_task` |
| `genesis-server/src/genesis_server/models/workflow_schedule.py` | `WorkflowSchedule` SQLModel table |
| `genesis-server/src/genesis_server/schemas/workflow_schedule.py` | `WorkflowScheduleCreate`, `WorkflowScheduleUpdate` with cron validation |
| `genesis-server/src/genesis_server/utils/workflow_job.py` | `add_workflow_job`, `run_workflow_job` utilities |
| `genesis-server/src/genesis_server/main.py` | Server startup calls `sm.sync_schedules()` |
| `genesis-core/src/genesis_core/workflow/workflow_engine.py` | `WorkflowEngine.run()` executes the workflow steps |
| `genesis-core/src/genesis_core/workflow/workflow_registry.py` | `WorkflowRegistry.get_workflow()` loads the manifest |