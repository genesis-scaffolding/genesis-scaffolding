import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from myproject_core.configs import get_config, settings
from myproject_core.logging_config import setup_logging

from .chat_manager import ChatManager
from .database import init_db
from .routers import (
    agents,
    auth,
    chat,
    files,
    jobs,
    llm_config,
    memory,
    productivity,
    schedules,
    users,
    workflows,
)
from .scheduler import SchedulerManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    setup_logging(config.log_level)
    logger.info("Starting MyProject API server")

    # 1. Initialize Database (Creates tables and Admin user)
    init_db()

    # 2. Initialize the Global Scheduler Manager
    sm = SchedulerManager()
    logger.debug("SchedulerManager initialized")

    # 3. Load all schedules from all users into the global scheduler
    await sm.sync_schedules()
    sm.start()
    logger.info("Scheduler started with %d jobs loaded", len(sm.scheduler.get_jobs()))

    # 4. Store in app state so routes can call sm.upsert_schedule/remove_schedule
    app.state.scheduler = sm

    # Initialize other global state
    app.state.chat_manager = ChatManager()
    logger.info("MyProject API server startup complete")

    yield

    # 5. Shutdown Logic
    logger.info("Shutting down MyProject API server")
    sm.stop()
    logger.info("MyProject API server shutdown complete")


app = FastAPI(title="MyProject API", lifespan=lifespan)

# Set up CORS using the safe list from our Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.all_cors_origins,
    allow_credentials=True,  # Required for Auth headers/cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)
app.include_router(workflows.router)
app.include_router(jobs.router)
app.include_router(schedules.router)
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(llm_config.router)
app.include_router(productivity.router)
app.include_router(memory.router)


@app.get("/health")
async def health_check():
    return {"status": "online"}
