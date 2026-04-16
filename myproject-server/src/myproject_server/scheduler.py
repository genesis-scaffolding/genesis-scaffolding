import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from myproject_core.agent.agent_registry import AgentRegistry
from myproject_core.configs import get_config
from myproject_core.configs import settings as server_settings
from myproject_core.workflow.workflow_engine import WorkflowEngine
from myproject_core.workflow.workflow_registry import WorkflowRegistry
from myproject_core.workflow.workflow_workspace import WorkspaceManager
from sqlmodel import Session, select

from .database import engine as db_engine
from .models.user import User
from .models.workflow_schedule import WorkflowSchedule
from .utils.workflow_job import add_workflow_job, run_workflow_job

logger = logging.getLogger(__name__)


class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def sync_schedules(self):
        """Initial sync on server start: Loads all enabled schedules for all users."""
        with Session(db_engine) as session:
            statement = select(WorkflowSchedule).where(WorkflowSchedule.enabled)
            for schedule in session.exec(statement).all():
                self.upsert_schedule(schedule)

    def upsert_schedule(self, schedule: WorkflowSchedule):
        job_id = f"sched_{schedule.id}"
        trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone=schedule.timezone)

        self.scheduler.add_job(
            self._execute_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=[schedule.id, schedule.user_id],  # Pass user_id to the task
            replace_existing=True,
        )

    def remove_schedule(self, schedule_id: int):
        try:
            self.scheduler.remove_job(f"sched_{schedule_id}")
        except Exception:
            pass

    async def _execute_scheduled_task(self, schedule_id: int, user_id: int):
        """The core logic: This function sets up the user's specific environment
        just-in-time for the execution.
        """
        with Session(db_engine) as session:
            # 1. Get the Schedule and User
            schedule = session.get(WorkflowSchedule, schedule_id)
            user = session.get(User, user_id)

            if not schedule or not schedule.enabled or not user:
                return

            # 2. RESOLVE USER CONTEXT
            # Get the user's specific directory and config
            user_workdir = server_settings.path.server_users_directory / str(user.id)
            user_config = get_config(user_workdir=user_workdir, override_yaml=user_workdir / "config.yaml")

            # Initialize user-specific components
            user_registry = WorkflowRegistry(user_config)
            user_agent_registry = AgentRegistry(user_config)
            user_wm = WorkspaceManager(user_config)
            user_engine = WorkflowEngine(user_wm, user_agent_registry, user_config.path.working_directory)

            # 3. Create the job record
            workflow_manifest = user_registry.get_workflow(schedule.workflow_id)
            if not workflow_manifest:
                logger.error(f"Workflow {schedule.workflow_id} not found for user {user.id}")
                return

            # Use the user_config's derived inbox
            user_inbox = user_config.path.working_directory

            job = await add_workflow_job(
                inputs=schedule.inputs,
                user_inbox=user_inbox,
                user_id=user_id,
                workflow_id=schedule.workflow_id,
                manifest=workflow_manifest,
            )

            if job and job.id:
                job.schedule_id = schedule.id
                schedule.last_run_at = datetime.now(UTC)
                session.add(job)
                session.add(schedule)
                session.commit()

                # 4. Run the job using the USER-SPECIFIC engine and registry
                await run_workflow_job(
                    job_id=job.id,
                    engine_instance=user_engine,
                    registry_instance=user_registry,
                )
