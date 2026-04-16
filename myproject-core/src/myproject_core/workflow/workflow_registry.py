import jinja2

from ..configs import Config, get_config
from ..schemas import WorkflowManifest
from ..utils import resolve_placeholders
from ..workflow_tasks.registry import TASK_LIBRARY


class WorkflowRegistry:
    def __init__(self, settings: Config):
        self.workflow_search_paths = settings.path.workflow_search_paths
        self.workflows: dict[str, WorkflowManifest] = {}
        self.load_all()

    def load_all(self):
        """Scans the directory and populates the registry."""
        for workflow_dir in self.workflow_search_paths:
            if not workflow_dir.exists():
                continue  # Ignore non-existent search path to avoid breaking workflow loading

            for yaml_file in workflow_dir.glob("*.yaml"):
                try:
                    # 1. Basic Pydantic validation
                    manifest = WorkflowManifest.from_yaml(yaml_file)

                    # 2. Step Type validation
                    self._verify_logic(manifest)

                    # 3. Register using the filename (stem) as the ID
                    self.workflows[yaml_file.stem] = manifest

                except Exception as e:
                    print(f"Error loading workflow '{yaml_file.name}': {e}")
                    continue  # Ignore non-compliant workflows to avoid breaking the system

    def _verify_logic(self, manifest: WorkflowManifest):
        """Dry-run Jinja2 templates using dummy data from Task models."""
        # 1. Mock the Blackboard
        fake_state = {"inputs": {k: v.default for k, v in manifest.inputs.items()}, "steps": {}}

        # 2. Populate 'steps' with dummy data based on output_models
        for step in manifest.steps:
            task_cls = TASK_LIBRARY.get(step.type)
            if not task_cls:
                raise ValueError(f"Task type '{step.type}' not found.")

            # Use model_json_schema to get keys, or model_construct for a dummy obj
            output_keys = task_cls.output_model.model_fields.keys()
            dummy_output = dict.fromkeys(output_keys, "dummy_val")

            fake_state["steps"][step.id] = dummy_output

        # Validate Step Params and Workflow Outputs
        try:
            for step in manifest.steps:
                resolve_placeholders(step.params, fake_state)

            # Check Workflow Outputs
            raw_outputs = {k: v.value for k, v in manifest.outputs.items()}
            resolve_placeholders(raw_outputs, fake_state)
        except jinja2.exceptions.UndefinedError as e:
            raise ValueError(f"Logic error: {e}") from e

    def get_workflow(self, name: str) -> WorkflowManifest | None:
        return self.workflows.get(name)

    def get_all_workflows(self) -> dict[str, WorkflowManifest]:
        return self.workflows


def main():
    settings = get_config()
    workflow_registry = WorkflowRegistry(settings)
    print(workflow_registry.workflows.keys())


if __name__ == "__main__":
    main()
