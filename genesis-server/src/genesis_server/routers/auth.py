from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from genesis_core.configs import Config

from genesis_server.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token_payload,
    verify_password,
)
from genesis_server.dependencies import SystemCoreDep, get_server_settings
from genesis_server.schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    system_core: SystemCoreDep,
    settings: Annotated[Config, Depends(get_server_settings)],
) -> Token:
    """Authenticate user and return JWT tokens."""
    # Fetch user from DB via system core's user manager
    user = system_core.user_manager.get_user_by_username(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.server.access_token_expire_minutes)
    access_token = create_access_token(subject=user.username, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(subject=user.username, expires_delta=access_token_expires)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.server.access_token_expire_minutes * 60,
        refresh_token=refresh_token,
    )


@router.post("/refresh")
async def refresh_access_token(
    system_core: SystemCoreDep,
    settings: Annotated[Config, Depends(get_server_settings)],
    refresh_token: str = Body(..., embed=True),
) -> Token:
    """Verify refresh token and issue a new access token."""
    [username, token_type] = decode_token_payload(refresh_token=refresh_token)

    if username is None or token_type is None or token_type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Verify user still exists
    user = system_core.user_manager.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Create new access token
    access_token_expires = timedelta(minutes=settings.server.access_token_expire_minutes)
    access_token = create_access_token(subject=username, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.server.access_token_expire_minutes * 60,
        refresh_token=refresh_token,
    )
