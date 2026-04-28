"""
System database setup for genesis_core.

Provides engine and session management for the shared system DB
(genesis.db). This is used for system-level tables: User, ChatSession,
ChatMessage, WorkflowJob, WorkflowSchedule.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from ..configs import Config

logger = logging.getLogger(__name__)

# Module-level engine, created on first use
_system_engine = None


def init_system_db(config: Config) -> None:
    """Create all system tables in the system DB."""
    global _system_engine

    if _system_engine is None:
        _system_engine = create_engine(
            config.db.connection_string,
            echo=config.db.echo_sql,
            connect_args={"check_same_thread": False}
            if config.db.connection_string.startswith("sqlite")
            else {},
        )

    # Import all system models to register them with SQLModel metadata
    from .models import ChatMessage, ChatSession, User, WorkflowJob, WorkflowSchedule  # noqa: F401

    SQLModel.metadata.create_all(_system_engine)
    logger.info("System DB initialized at %s", config.db.connection_string)
    logger.debug("SQLModel.metadata.tables: %s", list(SQLModel.metadata.tables.keys()))


def get_session() -> Generator:
    """Get a session for the system DB. Yields a SQLModel Session (FastAPI dependency style)."""
    if _system_engine is None:
        raise RuntimeError("System DB not initialized. Call init_system_db() first.")

    with Session(_system_engine) as session:
        yield session


@contextmanager
def get_session_context():
    """Context manager for system DB sessions (for use outside of FastAPI dependency injection)."""
    if _system_engine is None:
        raise RuntimeError("System DB not initialized. Call init_system_db() first.")

    with Session(_system_engine) as session:
        yield session

