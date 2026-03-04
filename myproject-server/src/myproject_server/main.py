from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from myproject_core.agent_registry import AgentRegistry
from myproject_core.configs import settings
from myproject_core.workflow_engine import WorkflowEngine
from myproject_core.workflow_registry import WorkflowRegistry
from myproject_core.workspace import WorkspaceManager

from .chat_manager import ChatManager
from .database import init_db
from .routers import agents, auth, chat, files, jobs, schedules, users, workflows
from .scheduler import SchedulerManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs on startup
    # Initialise databases
    init_db()
    # Initialize Core Workflow Infrastructure
    # workspace = WorkspaceManager(settings)
    # registry = WorkflowRegistry(settings)
    # agent_registry = AgentRegistry(settings)
    # engine = WorkflowEngine(workspace, agent_registry)
    #
    # # 3. Initialize & Start Scheduler
    # sm = SchedulerManager(engine, registry)
    #
    # # Load existing schedules from DB into memory
    # await sm.sync_schedules()
    # sm.start()

    # 4. Store in app state for dependencies
    # app.state.scheduler = sm

    chat_manager = ChatManager()
    app.state.chat_manager = chat_manager

    yield

    # 5. Shutdown Logic
    # sm.scheduler.shutdown(wait=False)
    # Cleanup logic (if any) goes here


app = FastAPI(title="MyProject API", lifespan=lifespan)

# Set up CORS using the safe list from our Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
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


@app.get("/health")
async def health_check():
    return {"status": "online"}
