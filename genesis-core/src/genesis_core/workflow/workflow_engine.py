import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any

from genesis_core.events import CoreEvent, CoreEventType, EventBus
from genesis_core.managers.workflow_job import WorkflowJobManager

from ..agent.agent_registry import AgentRegistry
from ..schemas import (
    JobContext,
    WorkflowCallback,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowManifest,
    WorkflowOutput,
)
from ..utils import evaluate_condition, resolve_placeholders
from ..workflow_tasks.registry import TASK_LIBRARY
from .workflow_registry import WorkflowRegistry
from .workflow_workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        agent_registry: AgentRegistry,
        working_directory: Path,
        workflow_registry: WorkflowRegistry,
        workflow_job_manager: WorkflowJobManager,
    ):
        self.workspace_manager = workspace_manager
        self.agent_registry = agent_registry
        self.working_directory = working_directory
        self.workflow_registry = workflow_registry
        self.workflow_job_manager = workflow_job_manager

    async def _run(
        self,
        manifest: WorkflowManifest,
        user_inputs: dict[str, Any],
        step_callbacks: list[WorkflowCallback] | None = None,
    ) -> WorkflowOutput:
        """Executes a validated workflow manifest."""
        logger.info("Workflow '%s' started with %d inputs", manifest.name, len(user_inputs))

        # Validate runtime input from user. Throw if validation fails
        validated_inputs = manifest.validate_runtime_inputs(user_inputs)

        # Initialize Workspace/Job
        job_context = self.workspace_manager.create_job(manifest.name)
        logger.debug("Workflow job created at: %s", job_context.root)

        # Initialize the "Blackboard" State
        state = {"inputs": validated_inputs, "steps": {}}

        # Iterate through steps
        for idx, step_def in enumerate(manifest.steps):
            # Check condition if present
            if step_def.condition and not evaluate_condition(step_def.condition, state):
                logger.debug("Step '%s' skipped due to condition evaluate to false", step_def.id)
                continue

            # Resolve placeholders in params using current state
            resolved_params = resolve_placeholders(step_def.params, state)

            # B. Get the Task class from the library
            task_class = TASK_LIBRARY[step_def.type]
            task_instance = task_class()

            # Use callback to communicate step starting
            logger.info(
                "Executing step %d/%d: '%s' (type: %s)",
                idx + 1,
                len(manifest.steps),
                step_def.id,
                step_def.type,
            )
            if step_callbacks:
                event = WorkflowEvent(
                    event_type=WorkflowEventType.STEP_START,
                    step_id=step_def.id,
                    message=f"Starting step: {step_def.id}",
                )
                await asyncio.gather(*(cb(event) for cb in step_callbacks))

            # Execute Task
            # We pass the job_context for file access and the resolved params for logic
            # Result output object is a pydantic object that matches the TaskOutput schema that a task define
            try:
                # Check if the .run method is native async
                if inspect.iscoroutinefunction(task_instance.run):
                    # It is async. We await it.
                    # Note: If the dev put blocking code inside here, it will still break the event loop
                    output = await task_instance.run(job_context, self.agent_registry, resolved_params)
                else:
                    # It is a standard 'def' (Synchronous).
                    # We automatically offload it to a thread to prevent blocking the caller.
                    output = await asyncio.to_thread(
                        task_instance.run,
                        job_context,
                        self.agent_registry,
                        resolved_params,
                    )
            except Exception as e:
                logger.error("Step '%s' failed: %s", step_def.id, e, exc_info=True)
                if step_callbacks:
                    event = WorkflowEvent(
                        event_type=WorkflowEventType.STEP_FAILED,
                        step_id=step_def.id,
                        message=f"Starting step: {step_def.id}",
                    )
                    await asyncio.gather(*(cb(event) for cb in step_callbacks))
                raise e

            # Update State
            state["steps"][step_def.id] = output.model_dump()

            # Checkpoint: Optional - save state to internal/state.json
            self._checkpoint(job_context, state)

            # Use callback to communicate step results
            if step_callbacks:
                event = WorkflowEvent(
                    event_type=WorkflowEventType.STEP_COMPLETED,
                    step_id=step_def.id,
                    message=f"Finished step: {step_def.id}",
                    data=output.model_dump(),  # Pass the actual output data
                )
                await asyncio.gather(*(cb(event) for cb in step_callbacks))

        # Create outputs — resolve both value and destination through Jinja2
        raw_outputs = {k: v.value for k, v in manifest.outputs.items()}
        workflow_output = resolve_placeholders(raw_outputs, state)

        # Resolve destinations (which may reference inputs or step outputs)
        resolved_destinations: dict[str, str | None] = {}
        for k, v in manifest.outputs.items():
            if v.destination is not None:
                resolved_destinations[k] = resolve_placeholders({k: v.destination}, state)[k]
            else:
                resolved_destinations[k] = None

        # Publish output files to the user's working directory
        from .workflow_publisher import OutputPublisher

        publisher = OutputPublisher(self.working_directory)
        await publisher.publish(manifest.outputs, workflow_output, resolved_destinations, job_context)

        logger.info("Workflow '%s' completed successfully", manifest.name)
        return WorkflowOutput(workflow_result=workflow_output, workspace_directory=job_context.root)

    def _checkpoint(self, context: JobContext, state: dict[str, Any]):
        """Persists the current state to the job directory for debugging/resume."""
        import json

        state_path = context.internal / "workflow_state.json"
        with open(state_path, "w") as f:
            # Note: You'll need a way to serialize complex objects if tasks return them
            json.dump(state, f, indent=2, default=str)

    async def run_workflow(
        self,
        user_id: int,
        workflow_id: str,
        inputs: dict[str, Any],
        event_bus: EventBus,
        job_id: int | None = None,
        callbacks: list[WorkflowCallback] | None = None,
    ) -> Any:
        """Run a workflow. Returns the completed job.

        Args:
            user_id: Owner of the workflow.
            workflow_id: Identifier of the workflow manifest to run.
            inputs: Runtime inputs passed to the workflow.
            event_bus: EventBus for streaming step events.
            job_id: If given, use this existing job record instead of creating a new one.
                    The job must exist and not be in a completed/failed state.
            callbacks: Optional workflow-level callbacks for step events. If not provided,
                       default callbacks that publish to event_bus are used.
        """
        manifest = self.workflow_registry.get_workflow(workflow_id)
        if not manifest:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        # Use existing job or create a new one
        if job_id is not None:
            existing = self.workflow_job_manager.get_job(job_id, user_id)
            if not existing:
                raise ValueError(f"Job {job_id} not found for user {user_id}")
            job = existing
        else:
            job = self.workflow_job_manager.create_job(
                user_id=user_id,
                workflow_id=workflow_id,
                inputs=inputs,
            )

        # Build callback list: use provided callbacks, or wrap event_bus if none given
        if callbacks is not None:
            step_callbacks: list[WorkflowCallback] = callbacks
        else:

            async def step_start_cb(event):
                await event_bus.publish(
                    CoreEvent(
                        event_type=CoreEventType.WORKFLOW_STEP_START,
                        workflow_id=workflow_id,
                        data={"step_id": event.step_id, "message": event.message},
                    )
                )

            async def step_complete_cb(event):
                await event_bus.publish(
                    CoreEvent(
                        event_type=CoreEventType.WORKFLOW_STEP_COMPLETED,
                        workflow_id=workflow_id,
                        data={"step_id": event.step_id, "data": event.data},
                    )
                )

            async def step_failed_cb(event):
                await event_bus.publish(
                    CoreEvent(
                        event_type=CoreEventType.WORKFLOW_STEP_FAILED,
                        workflow_id=workflow_id,
                        data={"step_id": event.step_id, "message": event.message},
                    )
                )

            async def wrapped_cb(event):
                if event.event_type == WorkflowEventType.STEP_START:
                    await step_start_cb(event)
                elif event.event_type == WorkflowEventType.STEP_COMPLETED:
                    await step_complete_cb(event)
                elif event.event_type == WorkflowEventType.STEP_FAILED:
                    await step_failed_cb(event)

            step_callbacks = [wrapped_cb]

        try:
            output = await self._run(manifest, inputs, step_callbacks=step_callbacks)
            resolved_job_id = job.id
            if resolved_job_id is None:
                raise RuntimeError("Job id was not set after creation")
            self.workflow_job_manager.mark_completed(resolved_job_id, user_id, output)
            return job
        except Exception as e:
            resolved_job_id = job.id
            if resolved_job_id is None:
                raise RuntimeError("Job id was not set after creation") from e
            self.workflow_job_manager.mark_failed(resolved_job_id, user_id, str(e))
            raise
