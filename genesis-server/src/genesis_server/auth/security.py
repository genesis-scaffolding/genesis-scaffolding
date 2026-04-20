from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from genesis_core.configs import settings
from pwdlib import PasswordHash

# Initialize the password hasher (Argon2id by default)
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.server.access_token_expire_minutes)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.server.jwt_secret_key, algorithm=settings.server.algorithm)
    return encoded_jwt


def create_refresh_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta + timedelta(days=1)
    else:
        expire = datetime.now(UTC) + timedelta(days=7)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.server.jwt_secret_key, algorithm=settings.server.algorithm)
    return encoded_jwt


def decode_token_payload(refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token, settings.server.jwt_secret_key, algorithms=[settings.server.algorithm],
        )
    except Exception:
        return [None, None]
    username: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")
    return [username, token_type]
