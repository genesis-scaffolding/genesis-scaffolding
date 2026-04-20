from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from genesis_core.configs import Config
from sqlmodel import Session, select

from genesis_server.dependencies import get_server_settings

from ..auth.security import create_access_token, create_refresh_token, decode_token_payload, verify_password
from ..database import get_session
from ..models.user import User
from ..schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Config, Depends(get_server_settings)],
) -> Token:
    # Fetch user from DB
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

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
        expires_in=settings.server.access_token_expire_minutes * 60,  # in seconds
        refresh_token=refresh_token,
    )


@router.post("/refresh")
async def refresh_access_token(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Config, Depends(get_server_settings)],
    refresh_token: str = Body(..., embed=True),
) -> Token:
    [username, token_type] = decode_token_payload(refresh_token=refresh_token)

    if username is None or token_type is None or token_type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Verify user still exists
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Create new access token
    access_token_expires = timedelta(minutes=settings.server.access_token_expire_minutes)
    access_token = create_access_token(subject=username, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.server.access_token_expire_minutes * 60,
        refresh_token=refresh_token,  # Return same refresh token (or create new one if you want rotation)
    )
