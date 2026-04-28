"""
GenesisCore: Unified API for interacting with genesis-core.

A per-user instance that owns registries, engines, managers, and the scheduler singleton.
Consumers (FastAPI, CLI) should ONLY interact with GenesisCore, never with internal components directly.
"""

import logging
from pathlib import Path
from typing import Any

from .agent.agent_engine import AgentEngine
from .agent.agent_registry import AgentRegistry
from .configs import get_config
from .database import init_system_db
from .database.models import ChatSession, WorkflowSchedule
from .events import EventBus
from .managers import (
    ChatSessionManager,
    MemoryManager,
    ProductivityManager,
    ScheduledJobManager,
    UserManager,
    WorkflowJobManager,
)
from .sandbox_filesystem.sandbox_filesystem import LocalSandboxFilesystem, SandboxFilesystem
from .scheduler import SchedulerManager
from .workflow.workflow_engine import WorkflowEngine
from .workflow.workflow_registry import WorkflowRegistry
from .workflow.workflow_workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class GenesisCore:
    """
    Unified API for genesis_core.

    Can be created in two modes:
    - System mode (user_id=None): for server/CLI bootstrap
    - User mode (user_id=int): per-user runtime with isolated registries, engines, managers

    All internal components are exposed directly for advanced consumers.
    For simple use cases, use the high-level methods on this class.
    """

    def __init__(
        self,
        user_id: int | None = None,
        working_directory: Path | None = None,
        yaml_override: Path | None = None,
        server_root_directory: Path | None = None,
    ):
        """
        Args:
            user_id: If None, this is a system-level instance for init/bootstrap.
                     If set, this is a per-user runtime instance.
            working_directory: User's working directory (where they open CLI/TUI).
            yaml_override: Optional path to user's config.yaml override.
            server_root_directory: Root of the installation. System DB lives at
                                   server_root_directory/.genesis/database/.
                                   If None, defaults to cwd.
        """
        logger.debug(
            "Running __init__ of GenesisCore with following inputs:\n- user_id: %s\n- working_directory: %s\n- yaml_override: %s\n- server_root_directory: %s\n",
            user_id,
            working_directory,
            yaml_override,
            server_root_directory,
        )
        self.user_id = user_id
        self.config = get_config(
            user_workdir=working_directory,
            override_yaml=yaml_override,
            server_root_directory=server_root_directory,
        )

        # Managers (created first, engines depend on them)
        self.user_manager = UserManager(self.config)
        self.chat_manager = ChatSessionManager(self.config)
        self.workflow_job_manager = WorkflowJobManager(self.config)
        self.scheduled_job_manager = ScheduledJobManager(self.config)
        self.productivity_manager = ProductivityManager(self.config)
        self.memory_manager = MemoryManager(self.config)

        # Registries (independent, created from config)
        self.agent_registry = AgentRegistry(self.config)
        self.workflow_registry = WorkflowRegistry(self.config)
        self.workspace_manager = WorkspaceManager(self.config)

        # Engines
        self.agent_engine = AgentEngine(self.config, self.agent_registry, self.chat_manager)
        self.workflow_engine = WorkflowEngine(
            self.workspace_manager,
            self.agent_registry,
            self.config.path.working_directory,
            self.workflow_registry,
            self.workflow_job_manager,
        )

        # Scheduler singleton: lazy acquisition
        self._scheduler: SchedulerManager | None = None

        # Sandbox filesystem: lazy creation
        self._sandbox_filesystem: SandboxFilesystem | None = None

        # Private DB init flag
        self._private_dbs_initialized = False

        # Event bus
        self.event_bus = EventBus()

    # --- BOOTSTRAP (system mode) ---

    async def init_system_db(self) -> None:
        """Initialize the system database (create tables, seed admin user)."""
        init_system_db(self.config)
        logger.info("System DB initialized")

    async def init_private_databases(self) -> None:
        """Initialize user-private databases (user_private.db, user_memory.db)."""
        from .persistent_memory.db import get_memory_engine
        from .productivity.db import get_user_engine

        get_user_engine(self.config)
        get_memory_engine(self.config)
        self._private_dbs_initialized = True
        logger.info("Private databases initialized")

    async def sync_schedules(self) -> None:
        """Load all enabled schedules from DB and register with APScheduler. Call once at startup."""
        scheduler = self.scheduler
        await scheduler.sync_schedules()
        scheduler.start()

    # --- CHAT ---

    def list_chat_sessions(self, agent_id: str | None = None) -> list[ChatSession]:
        """List all chat sessions for this user."""
        if self.user_id is None:
            raise ValueError("list_chat_sessions requires a user_id")
        return self.chat_manager.list_sessions(self.user_id, agent_id=agent_id)

    def create_chat_session(
        self,
        agent_id: str,
        title: str,
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> ChatSession:
        """Create a new chat session with an agent."""
        if self.user_id is None:
            raise ValueError("create_chat_session requires a user_id")
        if agent_id not in self.agent_registry.get_all_agent_types():
            raise ValueError(f"Agent '{agent_id}' not found")
        return self.chat_manager.create_session(
            self.user_id,
            agent_id,
            title,
            initial_messages=initial_messages,
        )

    def get_chat_session(self, session_id: int) -> tuple[ChatSession, list[Any]]:
        """Get a chat session with its messages."""
        if self.user_id is None:
            raise ValueError("get_chat_session requires a user_id")
        session = self.chat_manager.get_session(session_id, self.user_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        messages = self.chat_manager.get_messages(session_id, self.user_id)
        return session, messages

    async def run_agent(
        self,
        session_id: int,
        user_input: str,
        edit_index: int | None = None,
    ) -> None:
        """
        Run a single agent turn on a chat session.

        Caller should create an EventBus and subscribe to it to receive streamed events.
        """
        if self.user_id is None:
            raise ValueError("run_agent requires a user_id")
        event_bus = EventBus()
        await self.agent_engine.run(session_id, user_input, event_bus, edit_index=edit_index)

    # --- WORKFLOWS ---

    def list_workflows(self) -> list[Any]:
        """List all available workflow manifests."""
        return list(self.workflow_registry.get_all_workflows().values())

    def get_workflow(self, workflow_id: str) -> Any:
        """Get a specific workflow manifest."""
        return self.workflow_registry.get_workflow(workflow_id)

    def list_scheduled_workflows(self) -> list[WorkflowSchedule]:
        """List all scheduled workflows for this user."""
        if self.user_id is None:
            raise ValueError("list_scheduled_workflows requires a user_id")
        return self.scheduled_job_manager.list_schedules(self.user_id)

    def create_scheduled_workflow(
        self,
        workflow_id: str,
        name: str,
        cron_expression: str,
        inputs: dict[str, Any],
        timezone: str = "UTC",
        enabled: bool = True,
    ) -> WorkflowSchedule:
        """Create a scheduled workflow for this user."""
        if self.user_id is None:
            raise ValueError("create_scheduled_workflow requires a user_id")
        schedule = self.scheduled_job_manager.create_schedule(
            user_id=self.user_id,
            name=name,
            workflow_id=workflow_id,
            cron_expression=cron_expression,
            inputs=inputs,
            user_directory=str(self.config.path.working_directory),
            timezone=timezone,
            enabled=enabled,
        )
        self.scheduler.upsert_schedule(schedule)
        return schedule

    def delete_scheduled_workflow(self, schedule_id: int) -> bool:
        """Delete a scheduled workflow."""
        if self.user_id is None:
            raise ValueError("delete_scheduled_workflow requires a user_id")
        result = self.scheduled_job_manager.delete_schedule(schedule_id, self.user_id)
        if result:
            self.scheduler.remove_schedule(schedule_id)
        return result

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any]) -> Any:
        """Run a workflow. Returns the completed job."""
        if self.user_id is None:
            raise ValueError("run_workflow requires a user_id")

        await self.workflow_engine.run_workflow(
            self.user_id, workflow_id=workflow_id, inputs=inputs, event_bus=self.event_bus
        )

    # --- EVENTS ---

    def create_event_bus(self, session_id: int) -> EventBus:
        """Create a new event bus for streaming events for a session."""
        return EventBus()

    # --- SUBSYSTEM ACCESS (direct) ---

    @property
    def scheduler(self) -> SchedulerManager:
        """Create scheduler with injected managers on first access."""
        if self._scheduler is None:
            self._scheduler = SchedulerManager(
                scheduled_job_manager=self.scheduled_job_manager,
                workflow_job_manager=self.workflow_job_manager,
                workflow_engine=self.workflow_engine,
                event_bus=self.event_bus,
            )
        return self._scheduler

    @property
    def sandbox_filesystem(self) -> SandboxFilesystem:
        """Lazy sandbox filesystem tied to user's working_directory."""
        if self._sandbox_filesystem is None:
            self._sandbox_filesystem = LocalSandboxFilesystem(
                sandbox_root=self.config.path.working_directory,
                allow_symlinks_outside=True,
            )
        return self._sandbox_filesystem
