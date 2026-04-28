import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from genesis_core.configs import get_config, settings
from genesis_core.core import GenesisCore
from genesis_core.logging_config import setup_logging

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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    setup_logging(config.log_level)
    logger.info("Starting Genesis API server")

    # 1. Create system-level GenesisCore for bootstrapping
    #    This core has user_id=None and owns the system DB + scheduler
    system_core = GenesisCore(user_id=None, server_root_directory=config.path.server_root_directory)
    await system_core.init_system_db()
    await system_core.sync_schedules()
    system_core.scheduler.start()

    # 2. Cache the system core at None key, initialize user cores dict
    app.state.genesis_cores = {None: system_core}

    logger.info(
        "Genesis API server startup complete (scheduler: %d jobs)",
        len(system_core.scheduler.scheduler.get_jobs()),
    )

    yield

    # 3. Shutdown Logic
    logger.info("Shutting down Genesis API server")
    system_core.scheduler.stop()
    logger.info("Genesis API server shutdown complete")


app = FastAPI(title="Genesis API", lifespan=lifespan)

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

