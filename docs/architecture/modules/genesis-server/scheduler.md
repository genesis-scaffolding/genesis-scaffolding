# Scheduling

## Overview

The scheduling subsystem runs workflow jobs on cron schedules, independent of any API request lifecycle. A `Schedule` record acts as a factory — each cron trigger spawns a `WorkflowJob` record linked to the parent schedule. The background worker resolves user context at execution time, so agent and workflow updates take effect without server restart.

## Persistence Layer

Schedules are stored in the `workflow_schedule` table. At creation time, the API captures the user's current absolute sandbox path and IANA timezone. This allows the background worker to resolve relative file paths without access to FastAPI dependency injection.

## Scheduler Manager

Uses `APScheduler.AsyncIOScheduler` integrated into the FastAPI lifespan:

- **Lifespan Sync**: On server startup, `SchedulerManager` hydrates the in-memory schedule from the SQLite database
- **Real-time Mutation**: CRUD operations on schedules trigger immediate updates to `AsyncIOScheduler` — pause, resume, and frequency changes take effect without server restarts

## Execution Flow

1. **Trigger**: Cron expression fires based on the stored IANA timezone
2. **Spawn**: Manager creates a `WorkflowJob` record (status: `PENDING`) linked to `schedule_id`
3. **Resolve**: Manager uses the stored `user_directory` to expand file-based workflow inputs
4. **Execute**: `WorkflowEngine` is invoked with prepared inputs
5. **Traceability**: All results, logs, and artifacts are linked back to the parent Schedule

## Just-in-Time User Context

User config and registry are resolved **at execution time**, not at startup. When a cron trigger fires:

```
stored user_directory → load user_config.yaml → construct WorkflowRegistry → run job
```

If a user updates their agent definition or workflow manifest, the next scheduled run uses the new version immediately — no server restart required.

## Timezone Strategy

To ensure "9:00 AM" means the same thing regardless of server location:

- All timestamps stored as **naive UTC** in the database
- Frontend appends `Z` suffix to force browser-side UTC interpretation before converting to local display
- Cron triggers use the explicitly stored IANA timezone string (e.g., `Australia/Adelaide`) to calculate next execution offset

## REST Endpoints

See `schedules.py` router and `jobs.py` router for the API surface.

## Related Modules

- `genesis_server.scheduler` — `SchedulerManager` (APScheduler integration, job factory)
- `genesis_server.routers.schedules` — Schedule CRUD endpoints
- `genesis_server.routers.jobs` — Workflow job status and logs endpoints
- `genesis_core.scheduling` — Scheduling models and data structures
