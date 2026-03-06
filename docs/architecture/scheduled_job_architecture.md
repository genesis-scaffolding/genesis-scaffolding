# Automation & Scheduling Architecture

Genesis Scaffolding includes a built-in automation engine for recurring tasks, designed to run independently of the API request lifecycle.

## 1. The Persistence Layer
Automations are stored in the `workflow_schedule` table. Unlike manual jobs, a Schedule acts as a "Job Factory."
* **Context Preservation**: At creation time, the API captures the user's current absolute sandbox path and IANA timezone. This allows the background worker to resolve relative file paths without access to FastAPI dependency injection.

## 2. The Scheduler Manager
We utilize `APScheduler` (AsyncIOScheduler) integrated into the FastAPI lifespan:
* **Lifespan Sync**: On server startup, the `SchedulerManager` hydrates the in-memory schedule from the SQLite database.
* **Real-time Mutation**: CRUD operations on schedules trigger immediate updates to the `AsyncIOScheduler` instance, allowing "Pause/Resume" and "Edit Frequency" to take effect without server restarts.

## 3. Execution Flow
1. **Trigger**: The Cron expression hits based on the stored IANA Timezone.
2. **Spawn**: The manager creates a `WorkflowJob` record (status: `PENDING`) and links it to the `schedule_id`.
3. **Resolve**: The manager uses the stored `user_directory` to expand any file-based workflow inputs.
4. **Execute**: The `WorkflowEngine` is invoked with the prepared inputs.
5. **Traceability**: All results, logs, and artifacts are linked back to the parent Schedule, visible via the `GET /jobs?schedule_id=...` filter.

## 4. Timezone Strategy
To ensure "9:00 AM" means the same thing regardless of server location:
* All timestamps are stored as **Naive UTC** in the database.
* Frontend parsing (via `date-utils.ts`) appends the `Z` suffix to force browser-side UTC interpretation before converting to local display time.
* Cron triggers use the explicitly stored `timezone` string (e.g., `Australia/Adelaide`) to calculate the next execution offset.
