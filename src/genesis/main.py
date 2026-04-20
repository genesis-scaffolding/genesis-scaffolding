from genesis_cli.main import GenesisCLI
from genesis_core.agent.agent_registry import AgentRegistry
from genesis_core.configs import settings
from genesis_core.workflow.workflow_engine import WorkflowEngine
from genesis_core.workflow.workflow_registry import WorkflowRegistry
from genesis_core.workflow.workflow_workspace import WorkspaceManager


def start():
    """Logic for starting the code"""
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
