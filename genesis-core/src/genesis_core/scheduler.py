"""
System-wide scheduler for workflow cron jobs.

The SchedulerManager is a process-wide singleton. All DB access is delegated
to the managers injected at construction time — no direct database sessions.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from genesis_core.events import EventBus
from genesis_core.workflow.workflow_engine import WorkflowEngine

from .managers.scheduled_job import ScheduledJobManager
from .managers.workflow_job import WorkflowJobManager

logger = logging.getLogger(__name__)


class SchedulerManager:
    """System-wide scheduler for workflow cron jobs.

    Singleton — only one instance exists per process. All DB access goes through
    the injected managers:
    - scheduled_job_manager: for reading/updating schedules
    - workflow_job_manager: for creating/updating job records
    """

    _instance: "SchedulerManager | None" = None

    def __init__(
        self,
        scheduled_job_manager: ScheduledJobManager,
        workflow_job_manager: WorkflowJobManager,
        workflow_engine: WorkflowEngine,
        event_bus: EventBus,
    ):
        if SchedulerManager._instance is not None:
            raise RuntimeError("SchedulerManager is already instantiated")
        SchedulerManager._instance = self

        self._scheduled_job_manager = scheduled_job_manager
        self._workflow_job_manager = workflow_job_manager
        self._workflow_engine = workflow_engine
        self._event_bus = event_bus
        self._started = False
        self.scheduler = AsyncIOScheduler()

    @classmethod
    def get_instance(cls) -> "SchedulerManager":
        """Return the process-wide singleton. Raises if not yet created."""
        if cls._instance is None:
            raise RuntimeError("SchedulerManager not yet created")
        return cls._instance

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            self._started = True
            logger.info("SchedulerManager started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._started = False
            logger.info("SchedulerManager stopped")

    async def sync_schedules(self) -> None:
        """Load all enabled schedules from DB and register with APScheduler."""
        schedules = self._scheduled_job_manager.list_enabled_schedules()
        for schedule in schedules:
            self.upsert_schedule(schedule)
        logger.info("Synced %d schedules from DB", len(schedules))

    def upsert_schedule(self, schedule) -> None:
        """Register a schedule with APScheduler."""
        job_id = f"sched_{schedule.id}"
        trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone=schedule.timezone)

        self.scheduler.add_job(
            self._execute_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=[schedule.id],
            replace_existing=True,
        )
        logger.debug("Registered schedule %s (job_id=%s)", schedule.id, job_id)

    def remove_schedule(self, schedule_id: int) -> None:
        """Remove a schedule from APScheduler."""
        try:
            self.scheduler.remove_job(f"sched_{schedule_id}")
        except Exception:
            pass

    async def _execute_scheduled_task(self, schedule_id: int) -> None:
        """Execute a scheduled workflow. Called by APScheduler when cron fires."""
        logger.info("Scheduled task triggered: schedule_id=%s", schedule_id)
        # Load schedule via manager (no direct DB session)
        schedule = self._scheduled_job_manager.get_schedule_by_id(schedule_id)
        if not schedule or not schedule.enabled:
            logger.warning("Scheduled task %s skipped: schedule=%s or not enabled", schedule_id, schedule)
            return

        user_id = schedule.user_id
        workflow_id = schedule.workflow_id
        inputs = schedule.inputs or {}

        # Create the job record via manager (no direct DB session)
        job = self._workflow_job_manager.create_job(
            user_id=user_id,
            workflow_id=schedule.workflow_id,
            inputs=inputs,
            schedule_id=schedule_id,
        )
        job_id = job.id
        if job_id is None:
            raise RuntimeError("Job id was not set after creation")

        # Mark as running
        self._workflow_job_manager.mark_running(job_id, user_id)

        # Update last_run_at via manager
        self._scheduled_job_manager.update_last_run(schedule_id)

        # Run the workflow
        try:
            output = await self._workflow_engine.run_workflow(
                user_id=user_id, workflow_id=workflow_id, inputs=inputs, event_bus=self._event_bus,
            )
            self._workflow_job_manager.mark_completed(job_id, user_id, output)
            logger.info("Scheduled workflow %s completed for user %s", schedule.workflow_id, user_id)
        except Exception as e:
            self._workflow_job_manager.mark_failed(job_id, user_id, str(e))
            logger.error("Scheduled workflow %s failed for user %s: %s", schedule.workflow_id, user_id, e)