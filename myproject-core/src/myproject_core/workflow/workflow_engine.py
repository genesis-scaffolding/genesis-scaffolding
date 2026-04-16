import asyncio
import inspect
from pathlib import Path
from typing import Any

from ..agent.agent_registry import AgentRegistry
from ..configs import get_config
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


class WorkflowEngine:
    def __init__(
        self, workspace_manager: WorkspaceManager, agent_registry: AgentRegistry, working_directory: Path
    ):
        self.workspace_manager = workspace_manager
        self.agent_registry = agent_registry
        self.working_directory = working_directory

    async def run(
        self,
        manifest: WorkflowManifest,
        user_inputs: dict[str, Any],
        step_callbacks: list[WorkflowCallback] | None = None,
    ) -> WorkflowOutput:
        """Executes a validated workflow manifest."""
        # Validate runtime input from user. Throw if validation fails
        validated_inputs = manifest.validate_runtime_inputs(user_inputs)

        # Initialize Workspace/Job
        job_context = self.workspace_manager.create_job(manifest.name)

        # Initialize the "Blackboard" State
        state = {"inputs": validated_inputs, "steps": {}}

        # Iterate through steps
        for step_def in manifest.steps:
            # Check condition if present
            if step_def.condition and not evaluate_condition(step_def.condition, state):
                continue

            # Resolve placeholders in params using current state
            resolved_params = resolve_placeholders(step_def.params, state)

            # B. Get the Task class from the library
            task_class = TASK_LIBRARY[step_def.type]
            task_instance = task_class()

            # Use callback to communicate step starting
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

        return WorkflowOutput(workflow_result=workflow_output, workspace_directory=job_context.root)

    def _checkpoint(self, context: JobContext, state: dict[str, Any]):
        """Persists the current state to the job directory for debugging/resume."""
        import json

        state_path = context.internal / "workflow_state.json"
        with open(state_path, "w") as f:
            # Note: You'll need a way to serialize complex objects if tasks return them
            json.dump(state, f, indent=2, default=str)


async def main():
    settings = get_config()
    # 1. Setup managers
    wm = WorkspaceManager(settings)
    reg = WorkflowRegistry(settings)
    agent_reg = AgentRegistry(settings)
    engine = WorkflowEngine(wm, agent_reg, settings.path.working_directory)

    # 2. Pick the sample workflow
    manifest = reg.get_workflow("sample_workflow_multi_agent")
    if not manifest:
        print("Error: sample_workflow.yaml not found in registry.")
        return

    # 3. Simulate user input
    user_data = {
        "writing_topic": "An introduction to python monorepo, including concepts, benefits, and detailed guideline using uv",
        "content_length": 2000,
    }
    # 4. RUN
    print(f"Running workflow: {manifest.name}...")
    workflow_output = await engine.run(manifest, user_data)

    print("Workflow Complete!")
    print(f"{workflow_output}")


if __name__ == "__main__":
    asyncio.run(main())
