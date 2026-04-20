from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from genesis_core.schemas import WorkflowCallback, WorkflowInputType, WorkflowManifest
from genesis_core.workflow.workflow_engine import WorkflowEngine
from genesis_core.workflow.workflow_registry import WorkflowRegistry
from sqlmodel import Session

from ..database import engine as db_engine
from ..models.workflow_job import JobStatus, WorkflowJob


async def add_workflow_job(
    inputs: dict[str, Any],
    user_inbox: Path,
    user_id: int,
    workflow_id: str,
    manifest: WorkflowManifest,  # <--- Pass the manifest here
) -> WorkflowJob | None:
    """Register a workflow job in the database.
    Resolves relative paths to absolute sandbox paths based on the manifest definitions.
    """
    resolved_inputs = inputs.copy()

    # Iterate through the inputs defined in the manifest
    for input_name, definition in manifest.inputs.items():
        # Check if this specific input was actually provided by the user
        if input_name not in resolved_inputs or resolved_inputs[input_name] is None:
            continue

        val = resolved_inputs[input_name]

        # Handle List of Files
        if definition.type == WorkflowInputType.LIST_FILE:
            if isinstance(val, list):
                resolved_inputs[input_name] = [
                    str(user_inbox / f) if not Path(f).is_absolute() else f for f in val
                ]

        # Handle Single File or Directory
        elif definition.type in [WorkflowInputType.FILE, WorkflowInputType.DIR]:
            if isinstance(val, str):
                resolved_inputs[input_name] = str(user_inbox / val) if not Path(val).is_absolute() else val

    with Session(db_engine) as session:
        job = WorkflowJob(
            workflow_id=workflow_id,
            user_id=user_id,
            inputs=resolved_inputs,
            status=JobStatus.PENDING,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


async def run_workflow_job(
    job_id: int,
    engine_instance: WorkflowEngine,
    registry_instance: WorkflowRegistry,
    inputs: dict[str, Any] | None = None,
    workflow_callbacks: list[WorkflowCallback] | None = None,
) -> WorkflowJob | None:
    """Run a registered workflow job"""
    with Session(db_engine) as session:
        job = session.get(WorkflowJob, job_id)
        if not job:
            return None

        try:
            job.status = JobStatus.RUNNING
            session.add(job)
            session.commit()

            manifest = registry_instance.get_workflow(job.workflow_id)
            if not manifest:
                raise ValueError(f"Workflow type not found: {job.workflow_id}")

            # If user provides inputs, then use the input to run the workflow
            # Otherwise, try to use the input already registered in the database
            # If there is no workflow input to be found, throw exception
            workflow_inputs = job.inputs
            if inputs:
                workflow_inputs = inputs
            if not workflow_inputs:
                raise Exception(f"Could not find the inputs for workflow job {job_id}")

            workflow_output = await engine_instance.run(
                manifest,
                workflow_inputs,
                workflow_callbacks,
            )

            job.status = JobStatus.COMPLETED
            job.result = workflow_output.workflow_result
            job.workspace_path = str(workflow_output.workspace_directory)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
        finally:
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
        return job
