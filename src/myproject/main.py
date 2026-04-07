from myproject_cli.main import GenesisCLI
from myproject_core.agent_registry import AgentRegistry
from myproject_core.configs import settings
from myproject_core.workflow_engine import WorkflowEngine
from myproject_core.workflow_registry import WorkflowRegistry
from myproject_core.workspace import WorkspaceManager


def start():
    """Logic for starting the code
    """
    wm = WorkspaceManager(settings)
    registry = WorkflowRegistry(settings)
    agent_registry = AgentRegistry(settings)
    engine = WorkflowEngine(
        wm,
        agent_registry,
        settings.path.working_directory,
    )
    cli_app = GenesisCLI(settings, wm, registry, agent_registry, engine, settings.path.working_directory)

    cli_app()


if __name__ == "__main__":
    start()
