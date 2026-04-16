from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, create_engine

from ..configs import Config
from .models import memory_metadata

# FTS5 virtual table + triggers for full-text search
# This is executed after memory_metadata.create_all(engine) to set up FTS5.
# Split into individual statements — SQLite allows multiple statements but
# SQLAlchemy's text() can only execute one at a time.
_MEMORY_FTS_SETUP_SQL = [
    # Virtual table
    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
    "id, table_type, subject, content, superseded_by_id, "
    "tokenize='porter unicode61'"
    ")",
    # EventLog triggers
    "CREATE TRIGGER IF NOT EXISTS eventlog_ai AFTER INSERT ON eventlog BEGIN "
    "INSERT INTO memory_fts(id, table_type, subject, content, superseded_by_id) "
    "VALUES (new.id, 'event', new.subject, new.content, NULL); END",
    "CREATE TRIGGER IF NOT EXISTS eventlog_ad AFTER DELETE ON eventlog BEGIN "
    "DELETE FROM memory_fts WHERE id = old.id AND table_type = 'event'; END",
    "CREATE TRIGGER IF NOT EXISTS eventlog_au AFTER UPDATE ON eventlog BEGIN "
    "UPDATE memory_fts SET subject = new.subject, content = new.content "
    "WHERE id = new.id AND table_type = 'event'; END",
    # TopicalMemory triggers
    "CREATE TRIGGER IF NOT EXISTS topicalmemory_ai AFTER INSERT ON topicalmemory BEGIN "
    "INSERT INTO memory_fts(id, table_type, subject, content, superseded_by_id) "
    "VALUES (new.id, 'topic', new.subject, new.content, new.superseded_by_id); END",
    "CREATE TRIGGER IF NOT EXISTS topicalmemory_ad AFTER DELETE ON topicalmemory BEGIN "
    "DELETE FROM memory_fts WHERE id = old.id AND table_type = 'topic'; END",
    "CREATE TRIGGER IF NOT EXISTS topicalmemory_au AFTER UPDATE ON topicalmemory BEGIN "
    "UPDATE memory_fts SET subject = new.subject, content = new.content, "
    "superseded_by_id = new.superseded_by_id WHERE id = new.id AND table_type = 'topic'; END",
]

# Dictionary to keep track of initialized memory engines in a server context
# This prevents calling create_all multiple times for the same user in one process
_memory_engines = {}


def get_memory_engine(config: Config | None = None, memory_db_url: str | None = None, echo_sql=False):
    """Returns a SQLModel engine for the user's private memory database.
    Ensures the database and tables exist.

    Accepts either a Config object (from which the memory DB URL is derived)
    or an explicit memory_db_url string.
    """
    if memory_db_url is None and config is None:
        raise ValueError("Must provide either a Config object or a memory_db_url string.")
    target_url = memory_db_url or (config.memory_db.connection_string if config else None)
    assert target_url is not None, "memory_db_url must be set"

    if target_url not in _memory_engines:
        engine = create_engine(
            target_url,
            echo=echo_sql,
            # SQLite specific: Needed for multi-threaded apps (FastAPI)
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
        )
        # Initialize tables for this user's memory database
        memory_metadata.create_all(engine)

        # Set up FTS5 full-text search virtual table and sync triggers
        with engine.connect() as conn:
            for stmt in _MEMORY_FTS_SETUP_SQL:
                conn.execute(text(stmt))
            conn.commit()

        _memory_engines[target_url] = engine

    return _memory_engines[target_url]


def get_memory_session(
    config: Config | None = None,
    memory_db_url: str | None = None,
) -> Generator[Session, None, None]:
    """Context manager to get a memory session."""
    engine = get_memory_engine(config=config, memory_db_url=memory_db_url)
    with Session(engine) as session:
        yield session
