import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from genesis_core.configs import Config

from genesis_server.auth.security import get_password_hash, verify_password
from genesis_server.dependencies import SystemCoreDep, UserDep, get_server_settings
from genesis_server.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    system_core: SystemCoreDep,
    server_settings: Annotated[Config, Depends(get_server_settings)],
):
    """Create a new user. Checks if username already exists, hashes password, saves to DB."""
    # 1. Check for existing user
    existing = system_core.user_manager.get_user_by_username(user_in.username)
    if existing:
        raise HTTPException(
            status_code=400, detail="The user with this username already exists in the system.",
        )

    # 2. Create the DB record via user manager
    db_user = system_core.user_manager.create_user({
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
    })

    # 3. Create the sandbox directory asynchronously
    user_dir = Path(server_settings.path.server_users_directory) / str(db_user.id)
    await asyncio.to_thread(user_dir.mkdir, parents=True, exist_ok=True)

    # 4. Update working_directory
    assert db_user.id is not None
    updated = system_core.user_manager.update_user(db_user.id, working_directory=str(user_dir))
    return updated


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: UserDep,
):
    """Returns the current authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_user_me(
    user_update: UserUpdate,
    current_user: UserDep,
    system_core: SystemCoreDep,
):
    """Update current user information. If changing password, current_password must be verified."""
    update_data = user_update.model_dump(exclude_unset=True)

    # Handle Password Logic specifically
    if "new_password" in update_data:
        current_password = update_data.get("current_password")
        if not current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password.",
            )

        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password.",
            )

        update_data["hashed_password"] = get_password_hash(update_data.pop("new_password"))
        update_data.pop("current_password", None)

    # Apply all remaining fields via user manager
    if not current_user.id:
        raise HTTPException(status_code=400, detail="Current user has no ID")
    updated_user = system_core.user_manager.update_user(current_user.id, **update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user
