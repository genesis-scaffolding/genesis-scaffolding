import json
import logging
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from genesis_core.core import GenesisCore
from genesis_core.events import CoreEventType
from genesis_core.schemas import WorkflowCallback, WorkflowEvent, WorkflowEventType
from sse_starlette.sse import EventSourceResponse

from genesis_server.dependencies import CoreDep

logger = logging.getLogger(__name__)


class DatabaseProgressRenderer:
    """Implements WorkflowCallback to update step status in DB via core."""

    def __init__(self, job_id: int, user_id: int, core_ref):
        self.job_id = job_id
        self.user_id = user_id
        self.core_ref = core_ref

    async def __call__(self, event: WorkflowEvent) -> None:
        if not event.step_id:
            return
        mapping = {
            WorkflowEventType.STEP_START: "running",
            WorkflowEventType.STEP_COMPLETED: "completed",
            WorkflowEventType.STEP_FAILED: "failed",
        }
        new_status = mapping.get(event.event_type)
        if new_status:
            self.core_ref.workflow_job_manager.update_step_status(
                self.job_id,
                self.user_id,
                event.step_id,
                new_status,
            )


async def run_workflow_background(
    user_id: int,
    workflow_id: str,
    workflow_inputs: dict[str, Any],
    core_ref: GenesisCore,
    callbacks: list[WorkflowCallback],
    job_id: int,
):
    """Background task to run a workflow job."""
    try:
        await core_ref.workflow_engine.run_workflow(
            user_id=user_id,
            workflow_id=workflow_id,
            inputs=workflow_inputs,
            event_bus=core_ref.event_bus,
            job_id=job_id,
            callbacks=callbacks,
        )
    except Exception as e:
        logger.error("Workflow %s job %s failed: %s", workflow_id, job_id, e)


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _resolve_inputs(manifest, inputs: dict[str, Any], user_inbox: Path) -> dict[str, Any]:
    """Resolve relative input paths relative to user inbox."""
    from genesis_core.schemas import WorkflowInputType

    resolved = inputs.copy()
    for input_name, definition in manifest.inputs.items():
        if input_name not in resolved or resolved[input_name] is None:
            continue
        val = resolved[input_name]
        if definition.type == WorkflowInputType.LIST_FILE and isinstance(val, list):
            resolved[input_name] = [str(user_inbox / f) if not Path(f).is_absolute() else f for f in val]
        elif definition.type in [WorkflowInputType.FILE, WorkflowInputType.DIR] and isinstance(val, str):
            resolved[input_name] = str(user_inbox / val) if not Path(val).is_absolute() else val
    return resolved


@router.post("/")
async def submit_job(
    workflow_id: str,
    inputs: dict[str, Any],
    background_tasks: BackgroundTasks,
    core: CoreDep,
):
    """Submit a workflow job to run in the background."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    # Verify workflow exists
    manifest = core.workflow_registry.get_workflow(workflow_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Resolve inputs relative to inbox
    user_inbox = Path(core.config.path.working_directory)
    resolved_inputs = _resolve_inputs(manifest, inputs, user_inbox)

    # Create job record via manager
    job = core.workflow_job_manager.create_job(
        user_id=user_id,
        workflow_id=workflow_id,
        inputs=resolved_inputs,
    )
    safe_job_id = cast("int", job.id)
    safe_user_id = cast("int", user_id)

    # Prepare callbacks: only DatabaseProgressRenderer needed
    db_callback: WorkflowCallback = cast(
        WorkflowCallback, DatabaseProgressRenderer(safe_job_id, safe_user_id, core)
    )
    callbacks = [db_callback]

    # Dispatch background task
    background_tasks.add_task(
        run_workflow_background,
        safe_user_id,
        workflow_id,
        resolved_inputs,
        core,
        callbacks,
        safe_job_id,
    )

    return {"message": "Job submitted", "job_id": safe_job_id}


@router.get("/")
async def list_jobs(
    core: CoreDep,
    offset: int = 0,
    limit: int = 20,
    schedule_id: int | None = None,
):
    """Get all jobs for the current user, ordered by newest first."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")
    return core.workflow_job_manager.list_jobs(user_id, schedule_id=schedule_id)


@router.get("/{job_id}")
async def get_job_detail(
    job_id: int,
    core: CoreDep,
):
    """Get job details by ID."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")
    job = core.workflow_job_manager.get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/stream")
async def stream_job(job_id: int, core: CoreDep):
    """SSE stream for job step events from EventBus."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    # Verify job exists and belongs to user
    job = core.workflow_job_manager.get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Stream events from core.event_bus
        async for event in core.event_bus.on_workflow(job_id):
            if event.event_type == CoreEventType.WORKFLOW_STEP_START:
                yield {"event": "step_start", "data": json.dumps({"step_id": event.data.get("step_id"), "message": event.data.get("message")})}
            elif event.event_type == CoreEventType.WORKFLOW_STEP_COMPLETED:
                yield {"event": "step_completed", "data": json.dumps({"step_id": event.data.get("step_id"), "data": event.data.get("data")})}
            elif event.event_type == CoreEventType.WORKFLOW_STEP_FAILED:
                yield {"event": "step_failed", "data": json.dumps({"step_id": event.data.get("step_id"), "message": event.data.get("message")})}

    return EventSourceResponse(event_generator())


@router.get("/{job_id}/output")
async def list_job_outputs(
    job_id: int,
    core: CoreDep,
):
    """Lists files generated in the job's output sub-directory."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    job = core.workflow_job_manager.get_job(job_id, user_id)
    if not job or not job.workspace_path:
        raise HTTPException(status_code=404, detail="Workspace not found")

    output_dir = Path(job.workspace_path) / "output"
    if not output_dir.exists() or not output_dir.is_dir():
        return []

    results = []
    for full_path in output_dir.rglob("*"):
        if full_path.is_file():
            rel_path = full_path.relative_to(output_dir)
            results.append(
                {"name": full_path.name, "path": str(rel_path), "size": full_path.stat().st_size}
            )
    return results


@router.get("/{job_id}/output/download/{file_path:path}")
async def download_job_output(
    job_id: int,
    file_path: str,
    core: CoreDep,
):
    """Download a file from the job's output directory."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    job = core.workflow_job_manager.get_job(job_id, user_id)
    if not job or not job.workspace_path:
        raise HTTPException(status_code=404, detail="Job or workspace not found")

    workspace_root = Path(job.workspace_path).resolve()
    output_base = (workspace_root / "output").resolve()

    target_file = output_base / file_path
    try:
        if not target_file.resolve().is_relative_to(output_base):
            if not target_file.resolve().is_relative_to(workspace_root):
                raise HTTPException(status_code=403, detail="Access denied: outside of workspace scope")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied: outside of output scope") from exc

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(target_file, filename=target_file.name)
