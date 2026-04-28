"""
genesis_core.database package.

Provides system DB setup (engine, session, table creation) and all shared database models.
"""

from .system_db import get_session, get_session_context, init_system_db

__all__ = [
    "init_system_db",
    "get_session",
    "get_session_context",
]
