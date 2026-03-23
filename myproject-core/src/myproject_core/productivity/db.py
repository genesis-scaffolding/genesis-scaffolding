from typing import Generator

from sqlmodel import Session, create_engine

from ..configs import Config
from .models import productivity_metadata

# Dictionary to keep track of initialized user engines in a server context
# This prevents calling create_all multiple times for the same user in one process
_user_engines = {}


def get_user_engine(config: Config | None = None, db_url: str | None = None, echo_sql=False):
    """
    Returns a SQLModel engine for the user's private database.
    Ensures the database and tables exist.
    """
    target_url = db_url or (config.user_db.connection_string if config else None)

    if not target_url:
        raise ValueError("Must provide either a Config object or a db_url string.")

    if target_url not in _user_engines:
        engine = create_engine(
            target_url,
            echo=echo_sql,
            # SQLite specific: Needed for multi-threaded apps (FastAPI)
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
        )
        # Initialize tables for this specific user database
        productivity_metadata.create_all(engine)
        _user_engines[target_url] = engine

    return _user_engines[target_url]


def get_user_session(
    config: Config | None = None, db_url: str | None = None
) -> Generator[Session, None, None]:
    """Dependency or context manager to get a session."""
    engine = get_user_engine(config=config, db_url=db_url)
    with Session(engine) as session:
        yield session
