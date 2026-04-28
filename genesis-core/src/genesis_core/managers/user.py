"""
User subsystem manager for genesis_core.

Wraps the system database and provides CRUD operations for User.
"""

from typing import Any

from sqlmodel import select

from ..configs import Config
from ..database import get_session_context
from ..database.models import User


class UserManager:
    """Manager for user records (system DB)."""

    def __init__(self, config: Config):
        self.config = config

    def get_user_by_username(self, username: str) -> User | None:
        """Get a user by username (for auth)."""
        with get_session_context() as session:
            statement = select(User).where(User.username == username)
            return session.exec(statement).first()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get a user by ID."""
        with get_session_context() as session:
            return session.get(User, user_id)

    def create_user(self, data: dict[str, Any]) -> User:
        """Create a new user."""
        with get_session_context() as session:
            db_entry = User.model_validate(data)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def list_users(self, limit: int = 50, offset: int = 0) -> list[User]:
        """List all users."""
        with get_session_context() as session:
            statement = select(User).limit(limit).offset(offset)
            return list(session.exec(statement).all())

    def update_user(self, user_id: int, **kwargs) -> User | None:
        """Update user fields."""
        with get_session_context() as session:
            user = session.get(User, user_id)
            if not user:
                return None
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user