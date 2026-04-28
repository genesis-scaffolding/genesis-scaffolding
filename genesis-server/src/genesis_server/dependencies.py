"""
genesis_server dependencies.

All DB access goes through GenesisCore managers. Routers should only use
the dependencies defined here — no direct database imports.
"""
import logging
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from genesis_core.configs import Config, settings
from genesis_core.core import GenesisCore

from .models.user import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# -- Get server settings ---
async def get_server_settings() -> Config:
    return settings


# --- Get current authenticated user ---
async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Config, Depends(get_server_settings)],
) -> User:
    from jwt.exceptions import InvalidTokenError

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug("Attempting to decode JWT token")
        payload = jwt.decode(token, settings.server.jwt_secret_key, algorithms=[settings.server.algorithm])
        raw_sub = payload.get("sub")
        if not raw_sub:
            raise credentials_exception
        username: str = str(raw_sub)
    except InvalidTokenError as exc:
        logger.warning("InvalidTokenError encountered during JWT decode: %s", exc)
        raise credentials_exception from exc

    # Query the user via system core's user manager
    system_core: GenesisCore = request.app.state.genesis_cores[None]
    user = system_core.user_manager.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# --- GenesisCore access ---
async def get_genesis_core(request: Request) -> GenesisCore:
    """Returns the system-level GenesisCore (for bootstrap/admin operations)."""
    return request.app.state.genesis_cores[None]


async def get_user_genesis_core(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> GenesisCore:
    """Returns the per-user GenesisCore, creating it on first access."""
    user_id = current_user.id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    cores = request.app.state.genesis_cores
    if user_id not in cores:
        user_workdir = settings.path.server_users_directory / str(user_id)
        cores[user_id] = GenesisCore(
            user_id=user_id,
            working_directory=user_workdir,
            yaml_override=user_workdir / "config.yaml",
            server_root_directory=settings.path.server_root_directory,
        )
        await cores[user_id].init_private_databases()
        logger.info("Created GenesisCore for user %s", user_id)

    return cores[user_id]


# --- User Isolation ---
async def get_user_workdir(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Path:
    """Base directory for a specific user."""
    user_path = settings.path.server_users_directory / str(current_user.id)
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


async def get_user_inbox_path(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Path:
    """User's private inbox (working directory)."""
    inbox_path = settings.path.server_users_directory / str(current_user.id)
    inbox_path.mkdir(parents=True, exist_ok=True)
    return inbox_path


# --- Type aliases for routes ---
UserDep = Annotated[User, Depends(get_current_active_user)]
InboxDep = Annotated[Path, Depends(get_user_inbox_path)]
CoreDep = Annotated[GenesisCore, Depends(get_user_genesis_core)]
SystemCoreDep = Annotated[GenesisCore, Depends(get_genesis_core)]
