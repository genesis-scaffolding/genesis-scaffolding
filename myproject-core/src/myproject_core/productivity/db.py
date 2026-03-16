from typing import Generator

from sqlmodel import Session, create_engine

from ..configs import Config
from .models import productivity_metadata

# Dictionary to keep track of initialized user engines in a server context
# This prevents calling create_all multiple times for the same user in one process
_user_engines = {}


def get_user_engine(config: Config):
    """
    Returns a SQLModel engine for the user's private database.
    Ensures the database and tables exist.
    """
    db_url = config.user_db.connection_string

    if db_url not in _user_engines:
        engine = create_engine(
            db_url,
            echo=config.user_db.echo_sql,
            # SQLite specific: Needed for multi-threaded apps (FastAPI)
            connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        )
        # Initialize tables for this specific user database
        productivity_metadata.create_all(engine)
        _user_engines[db_url] = engine

    return _user_engines[db_url]


def get_user_session(config: Config) -> Generator[Session, None, None]:
    """Dependency or context manager to get a session."""
    engine = get_user_engine(config)
    with Session(engine) as session:
        yield session
