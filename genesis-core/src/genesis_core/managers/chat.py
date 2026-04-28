"""
Chat session subsystem manager for genesis_core.

Wraps the system database and provides CRUD operations for ChatSession and ChatMessage.
"""

from datetime import UTC, datetime
from typing import Any

from sqlmodel import col, select

from ..configs import Config
from ..database import get_session_context
from ..database.models import ChatMessage, ChatSession


class ChatSessionManager:
    """Manager for chat sessions and messages (system DB)."""

    def __init__(self, config: Config):
        self.config = config

    def list_sessions(self, user_id: int, agent_id: str | None = None) -> list[ChatSession]:
        """List all chat sessions for a user, optionally filtered by agent."""
        with get_session_context() as session:
            statement = (
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(col(ChatSession.updated_at).desc())
            )
            if agent_id:
                statement = statement.where(ChatSession.agent_id == agent_id)
            return list(session.exec(statement).all())

    def get_session(self, session_id: int, user_id: int) -> ChatSession | None:
        """Get a chat session by ID, ensuring it belongs to the user."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return None
            return chat_session

    def create_session(
        self,
        user_id: int,
        agent_id: str,
        title: str,
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> ChatSession:
        """Create a new chat session, optionally with initial messages."""
        with get_session_context() as session:
            new_session = ChatSession(
                user_id=user_id,
                agent_id=agent_id,
                title=title,
            )
            session.add(new_session)
            session.flush()

            session.commit()
            session.refresh(new_session)
            session_id = new_session.id
            if session_id is None:
                raise RuntimeError("Failed to create chat session")

            if initial_messages:
                for msg in initial_messages:
                    db_msg = ChatMessage(
                        session_id=session_id,
                        payload=msg,
                    )
                    session.add(db_msg)
                session.commit()

            return new_session

    def update_session(self, session_id: int, user_id: int, **kwargs) -> ChatSession | None:
        """Update session fields."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return None
            for key, value in kwargs.items():
                if hasattr(chat_session, key):
                    setattr(chat_session, key, value)
            chat_session.updated_at = datetime.now(UTC)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def delete_session(self, session_id: int, user_id: int) -> bool:
        """Delete a chat session and all its messages."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return False
            session.delete(chat_session)
            session.commit()
            return True

    def get_messages(self, session_id: int, user_id: int) -> list[ChatMessage]:
        """Get all messages for a session."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return []
            return list(
                session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(col(ChatMessage.id).asc())
                ).all()
            )

    def add_message(self, session_id: int, user_id: int, payload: dict[str, Any]) -> ChatMessage | None:
        """Add a single message to a session."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return None
            db_msg = ChatMessage(session_id=session_id, payload=payload)
            session.add(db_msg)
            chat_session.updated_at = datetime.now(UTC)
            session.add(chat_session)
            session.commit()
            session.refresh(db_msg)
            return db_msg

    def add_messages(
        self,
        session_id: int,
        user_id: int,
        messages: list[dict[str, Any]],
    ) -> list[ChatMessage]:
        """Add multiple messages to a session atomically."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return []
            db_msgs = []
            for msg in messages:
                db_msg = ChatMessage(session_id=session_id, payload=msg)
                session.add(db_msg)
                db_msgs.append(db_msg)
            chat_session.updated_at = datetime.now(UTC)
            session.add(chat_session)
            session.commit()
            for db_msg in db_msgs:
                session.refresh(db_msg)
            return db_msgs

    def delete_messages_after(self, session_id: int, user_id: int, message_id: int) -> bool:
        """Delete all messages from message_id onwards."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return False
            # Delete all messages from message_id onwards
            for msg in session.query(ChatMessage).filter(col(ChatMessage.id) >= message_id).all():
                session.delete(msg)
            session.commit()
            return True

    def get_user_id_from_session(self, session_id: int) -> int | None:
        """Quick helper to get user_id from a session without full load."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session.user_id if chat_session else None

    def update_clipboard_state(
        self,
        session_id: int,
        user_id: int,
        clipboard_state: dict[str, Any],
    ) -> bool:
        """Update the clipboard state for a session."""
        with get_session_context() as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session or chat_session.user_id != user_id:
                return False
            chat_session.clipboard_state = clipboard_state
            chat_session.updated_at = datetime.now(UTC)
            session.add(chat_session)
            session.commit()
            return True
