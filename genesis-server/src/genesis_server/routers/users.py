import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from genesis_core.configs import Config
from sqlmodel import Session, select

from ..auth.security import get_password_hash, verify_password
from ..database import get_session
from ..dependencies import get_current_active_user, get_server_settings
from ..models.user import User
from ..schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: Annotated[Session, Depends(get_session)],
    server_settings: Annotated[Config, Depends(get_server_settings)],
):
    """Create a new user.
    Checks if username already exists, hashes password, and saves to DB.
    """
    # 1. Check for existing user
    existing_user = session.exec(select(User).where(User.username == user_in.username)).first()

    if existing_user:
        raise HTTPException(
            status_code=400, detail="The user with this username already exists in the system.",
        )

    # 2. Create the DB record
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),  # Hash it!
    )

    # Commit first so the database assigns an ID to db_user.id
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    # 3. Create the sandbox directory asynchronously
    server_users_directory = server_settings.path.server_users_directory

    # Construct the path: <server_users_directory>/<user_id>
    user_dir = Path(server_users_directory) / str(db_user.id)

    # Use asyncio.to_thread to run the blocking os/pathlib mkdir call in a background thread.
    await asyncio.to_thread(user_dir.mkdir, parents=True, exist_ok=True)

    # 4. Save the directory path back to the user record
    db_user.working_directory = str(user_dir)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Returns the current authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Update current user information.
    If changing password, current_password must be verified.
    """
    # 1. Convert input to a dictionary, ignoring fields NOT in the JSON
    update_data = user_update.model_dump(exclude_unset=True)

    # 2. Handle Password Logic specifically
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

        # Hash the new password and replace the plain text one in our update dict
        update_data["hashed_password"] = get_password_hash(update_data.pop("new_password"))
        # Remove current_password so we don't try to save it to the User model
        update_data.pop("current_password", None)

    # 3. Apply all remaining fields to the DB object
    for key, value in update_data.items():
        setattr(current_user, key, value)

    # 4. Save changes
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user
