from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from myproject_core.agent_registry import AgentRegistry
from myproject_core.configs import Config, get_config, settings
from myproject_core.productivity.db import get_user_session
from myproject_core.workflow_engine import WorkflowEngine
from myproject_core.workflow_registry import WorkflowRegistry
from myproject_core.workspace import WorkspaceManager
from sqlmodel import Session, select

from .database import get_session
from .models.user import User
from .scheduler import SchedulerManager
from .schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# -- Get server settings ---
async def get_server_settings() -> Config:
    return settings


# --- Get current authenticated user ---
async def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Config, Depends(get_server_settings)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(token)
        print(settings.server.jwt_secret_key)
        print(settings.server.algorithm)
        payload = jwt.decode(token, settings.server.jwt_secret_key, algorithms=[settings.server.algorithm])
        if not payload.get("sub"):
            raise credentials_exception
        username: str = str(payload.get("sub"))
        token_data = TokenData(username=username)
    except InvalidTokenError:
        print("InvalidTokenError encountered")
        raise credentials_exception

    # Query the actual database
    statement = select(User).where(User.username == token_data.username)
    user = session.exec(statement).first()

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# --- User Isolation Logic ---


async def get_user_workdir(
    current_user: Annotated[User, Depends(get_current_active_user)],
    settings: Annotated[Config, Depends(get_server_settings)],
) -> Path:
    """Determines the base directory for a specific user.
    Uses the global 'server_users_directory' defined in the server's settings.
    """
    # Use the global settings to find where user folders are stored
    base_user_dir = settings.path.server_users_directory

    # We use user.id (or username) to create a unique sub-folder
    user_path = base_user_dir / str(current_user.id)
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


async def get_user_config(
    user_workdir: Annotated[Path, Depends(get_user_workdir)],
) -> Config:
    """Creates a specialized Config object for the current user.
    It looks for a 'config.yaml' inside the user's working directory.
    """
    # Path to the user's optional override config
    user_override_yaml = user_workdir / "config.yaml"
    # Generate a config instance tailored to this user's path
    # get_config will handle merging global defaults with user overrides
    user_specific_settings = get_config(user_workdir=user_workdir, override_yaml=user_override_yaml)

    return user_specific_settings


async def get_user_inbox_path(
    user_config: Annotated[Config, Depends(get_user_config)],
) -> Path:
    """Returns the resolved Path for the user's private inbox.
    Now dynamically derived from the user's config.
    """
    # Use user working directory as the inbox
    # The reason I did not rename get_user_inbox_path is because I don't want to deal with random breaking across the server code
    inbox_path = user_config.path.working_directory
    inbox_path.mkdir(parents=True, exist_ok=True)
    return inbox_path


def get_productivity_session(
    user_config: Annotated[Config, Depends(get_user_config)],
):
    """Returns a session for the user's private productivity database.
    Because get_user_session is a generator, we 'yield from' it.
    """
    yield from get_user_session(user_config)


# --- User-Specific Manager Injections ---


async def get_agent_registry(user_config: Annotated[Config, Depends(get_user_config)]) -> AgentRegistry:
    """Returns an AgentRegistry scoped to the current user's paths and settings.
    """
    return AgentRegistry(user_config)


async def get_workflow_registry(
    user_config: Annotated[Config, Depends(get_user_config)],
) -> WorkflowRegistry:
    """Returns a WorkflowRegistry scoped to the current user's paths and settings.
    """
    return WorkflowRegistry(user_config)


async def get_workspace_manager(
    user_config: Annotated[Config, Depends(get_user_config)],
) -> WorkspaceManager:
    """Returns a WorkspaceManager pointing to the user's private workspace directory.
    """
    return WorkspaceManager(user_config)


async def get_workflow_engine(
    wm: Annotated[WorkspaceManager, Depends(get_workspace_manager)],
    agent_reg: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> WorkflowEngine:
    """Returns a WorkflowEngine initialized with the user's specific workspace and agents.
    """
    return WorkflowEngine(wm, agent_reg)


# --- System-Level Injections ---


async def get_scheduler_manager(request: Request) -> SchedulerManager:
    """The Scheduler usually remains a global system-level service (app.state),
    as it manages background threads/processes across all users.
    """
    return request.app.state.scheduler


# --- Updated Type Aliases for Clean Routers ---

# Use these in your path operations for cleaner signatures
UserConfigDep = Annotated[Config, Depends(get_user_config)]
AgentRegDep = Annotated[AgentRegistry, Depends(get_agent_registry)]
WorkflowRegDep = Annotated[WorkflowRegistry, Depends(get_workflow_registry)]
WorkspaceDep = Annotated[WorkspaceManager, Depends(get_workspace_manager)]
EngineDep = Annotated[WorkflowEngine, Depends(get_workflow_engine)]
ProdSessionDep = Annotated[Session, Depends(get_productivity_session)]


async def get_memory_session(
    user_config: Annotated[Config, Depends(get_user_config)],
):
    """Returns a session for the user's private memory database."""
    from myproject_core.memory.db import get_memory_engine
    engine = get_memory_engine(config=user_config)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


MemorySessionDep = Annotated[Session, Depends(get_memory_session)]
