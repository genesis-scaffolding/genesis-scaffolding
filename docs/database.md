# Database Architecture

This document describes the database architecture, the SQLModel ORM layer, and how to work with databases in this codebase. For database-related configuration, see [settings.md](./settings.md).

---

## Three Databases

The system uses three separate SQLite databases. Each database is managed by a different layer of the codebase.

| Database | Managed by | Connection | Purpose | Key Models |
|---|---|---|---|---|
| System | `genesis-server` | `config.db` | Auth, chat, jobs, schedules | `User`, `ChatSession`, `ChatMessage` |
| User productivity | `genesis-core` | `config.user_db` | Tasks, projects, journals | `Task`, `Project`, `JournalEntry` |
| User memory | `genesis-core` | `config.memory_db` | Agent memory with full-text search | `EventLog`, `TopicalMemory` |

System DB lives at the server root `.genesis/database/genesis.db`. User productivity and memory databases live inside each user's sandbox `.genesis/` directory. This means each user gets their own isolated productivity and memory data.

The three databases are configured in `genesis-core/src/genesis_core/configs.py` under the `Config` model.

**Important distinction:**
- Only `genesis-core` productivity and memory subsystems follow the `db.py / models.py / service.py` pattern described in later sections of this doc.
- System DB models and database access are defined entirely in `genesis-server`. If you need to add or modify system DB models (users, chat, jobs, schedules), look in `genesis-server/src/genesis_server/models/` and `genesis-server/src/genesis_server/database.py` instead.

---

## SQLModel ORM Layer

### What is an ORM

An ORM (Object-Relational Mapper) bridges the gap between Python objects and database tables. Instead of writing raw SQL, you define Python classes that map to tables, and the ORM handles the translation.

SQLModel builds on top of SQLAlchemy, adding Pydantic-compatible model definitions. Use SQLModel only — avoid importing from `sqlalchemy` directly when defining models or writing queries, except for specific advanced cases documented below. SQLAlchemy and SQLModel share many function names with different behaviors, which makes debugging errors difficult.

### How SQLModel Creates Tables

SQLModel uses SQLAlchemy `MetaData` to track table definitions. When you call `MyMetadata.create_all(engine)`, SQLAlchemy reads all models linked to that metadata and issues `CREATE TABLE IF NOT EXISTS` statements for any missing tables. This is a one-way migration: it creates tables but never alters or drops them.

### Defining Models

All models inherit from `SQLModel` and use `Field` to define columns:

```python
from sqlmodel import Field, SQLModel

class MyModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    status: str = Field(default="active")
```

**Key points:**
- `table=True` marks this as a database table. Without it, the class is just a Pydantic model.
- `Field(default=None, primary_key=True)` creates an auto-incrementing integer primary key.
- `Field(index=True)` creates a database index on that column.
- Use `str | None` for nullable columns, `str` for required columns.

**Foreign keys and relationships** require a shared `MetaData` instance across the related models:

```python
from sqlalchemy import MetaData
from sqlmodel import Field, Relationship, SQLModel

my_metadata = MetaData()  # one per subsystem

class Parent(SQLModel, table=True):
    metadata = my_metadata
    id: int | None = Field(default=None, primary_key=True)
    children: list["Child"] = Relationship(back_populates="parent")

class Child(SQLModel, table=True):
    metadata = my_metadata
    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="parent.id")
    parent: Parent | None = Relationship(back_populates="children")
```

**JSON columns** for lists or dicts:

```python
from sqlalchemy import Column
from sqlmodel import JSON, Field

class MyModel(SQLModel, table=True):
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
```

**Timezone-aware timestamps:**

```python
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime
from sqlmodel import Field

def get_utc_now():
    return datetime.now(UTC)

class MyModel(SQLModel, table=True):
    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True)),
    )
```

### Engine and Session

An engine represents a connection to a specific database file or server. Sessions are short-lived objects that represent a unit of work against that database.

```python
from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///mydb.db", connect_args={"check_same_thread": False})
session = Session(engine)
```

**Cache engines at module level** so tables are only created once:

```python
_engines: dict[str, Engine] = {}

def get_my_engine(db_url: str):
    if db_url not in _engines:
        engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
        MyMetadata.create_all(engine)
        _engines[db_url] = engine
    return _engines[db_url]
```

### CRUD Operations

**Read by primary key:**

```python
item = session.get(MyModel, item_id)
```

**Select with filters:**

```python
from sqlmodel import select

statement = select(MyModel).where(MyModel.status == "active")
results = session.exec(statement).all()
```

**Select with relationships loaded:**

```python
from sqlalchemy.orm import selectinload

statement = select(Task).where(Task.id == task_id).options(selectinload(Task.projects))
task = session.exec(statement).first()
```

**Create:**

```python
db_item = MyModel.model_validate(data)
session.add(db_item)
session.commit()
session.refresh(db_item)
```

**Update:**

```python
db_item = session.get(MyModel, item_id)
for key, value in data.items():
    if hasattr(db_item, key):
        setattr(db_item, key, value)
session.add(db_item)
session.commit()
session.refresh(db_item)
```

For partial updates from Pydantic input:

```python
update_data = data.model_dump(exclude_unset=True, mode="python")
for key, value in update_data.items():
    setattr(db_item, key, value)
```

**Delete:**

```python
db_item = session.get(MyModel, item_id)
session.delete(db_item)
session.commit()
```

---

## Models in This Codebase

### System DB Models (genesis-server)

These live under `genesis-server/src/genesis_server/models/`:

| Model | File | Purpose |
|---|---|---|
| `User` | `models/user.py` | User accounts and auth |
| `ChatSession` | `models/chat.py` | Chat session records |
| `ChatMessage` | `models/chat.py` | Individual chat messages |
| `WorkflowJob` | `models/workflow_job.py` | Workflow run records |
| `WorkflowSchedule` | `models/workflow_schedule.py` | Cron-based workflow schedules |
| `FileRecord` | `models/file_record.py` | Uploaded file metadata |

Database setup and session management are in `genesis-server/src/genesis_server/database.py`.

### Productivity Models (genesis-core)

These live under `genesis-core/src/genesis_core/productivity/`:

| Model | File | Purpose |
|---|---|---|
| `Task` | `models.py` | Task items with deadlines and scheduling |
| `Project` | `models.py` | Projects that contain tasks |
| `JournalEntry` | `models.py` | Journal entries (daily, weekly, project) |
| `ProjectTaskLink` | `models.py` | Many-to-many link between tasks and projects |

Database setup is in `db.py`, CRUD logic in `service.py`.

### Memory Models (genesis-core)

These live under `genesis-core/src/genesis_core/persistent_memory/`:

| Model | File | Purpose |
|---|---|---|
| `EventLog` | `models.py` | Append-only log of events and facts |
| `TopicalMemory` | `models.py` | Revisable knowledge entries with supersession chain |

Database setup with FTS5 full-text search is in `db.py`, CRUD logic in `service.py`.

---

## Setting Up Engines and Sessions

### System DB

System DB uses a module-level engine in `genesis-server/src/genesis_server/database.py`:

```python
engine = create_engine(str(settings.db.connection_string), echo=settings.db.echo_sql)
SQLModel.metadata.create_all(engine)
```

FastAPI dependency:

```python
def get_session():
    with Session(engine) as session:
        yield session
```

### User Databases (genesis-core pattern)

Each subsystem in `genesis-core` follows this structure:

```
genesis-core/src/genesis_core/<subsystem>/
    models.py   # SQLModel table definitions
    db.py       # engine and session utilities
    service.py  # CRUD functions
```

**Engine and session** in `db.py`:

```python
_engines: dict[str, Engine] = {}

def get_engine(config: Config | None = None, db_url: str | None = None):
    target_url = db_url or config.user_db.connection_string
    if target_url not in _engines:
        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
        )
        SubsystemMetadata.create_all(engine)
        _engines[target_url] = engine
    return _engines[target_url]

def get_session(...) -> Generator[Session, None, None]:
    engine = get_engine(...)
    with Session(engine) as session:
        yield session
```

### FastAPI Dependency Injection

In `genesis-server/src/genesis_server/dependencies.py`:

```python
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session
from genesis_core.productivity.db import get_user_session
from genesis_core.persistent_memory.db import get_memory_engine
from genesis_core.configs import get_config, Config

def get_user_config(user_workdir: Path, ...) -> Config:
    return get_config(user_workdir=user_workdir, override_yaml=user_override_yaml)

def get_productivity_session(user_config: Annotated[Config, Depends(get_user_config)]):
    yield from get_user_session(user_config)

ProdSessionDep = Annotated[Session, Depends(get_productivity_session)]

def get_memory_session(user_config: Annotated[Config, Depends(get_user_config)]):
    engine = get_memory_engine(config=user_config)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

MemorySessionDep = Annotated[Session, Depends(get_memory_session)]
```

Use in routes:

```python
@router.get("/tasks")
def list_tasks(session: ProdSessionDep):
    return session.exec(select(Task)).all()
```

### Session in Tools

Tools receive `user_db_url` and `memory_db_url` from the agent harness:

```python
async def run(
    self,
    working_directory: Path,
    user_db_url: str | None = None,
    memory_db_url: str | None = None,
    **kwargs,
) -> ToolResult:
    if not user_db_url:
        return ToolResult(status="error", tool_response="Productivity not enabled")

    with Session(get_user_engine(db_url=user_db_url)) as session:
        results = session.exec(select(Task)).all()
        # ...
```

---

## Service Layer

CRUD logic lives in `genesis-core/src/<subsystem>/service.py`. This separates query logic from FastAPI routes and makes it reusable by both routes and tools.

```python
from sqlmodel import Session, select

def get_item(session: Session, item_id: int) -> MyModel | None:
    return session.get(MyModel, item_id)

def list_items(session: Session) -> list[MyModel]:
    return list(session.exec(select(MyModel)).all())

def create_item(session: Session, data: dict) -> MyModel:
    db_item = MyModel.model_validate(data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
```

---

## User Isolation

Per-user databases are resolved via `get_config(user_workdir=..., override_yaml=...)`, which merges server-wide defaults with user-specific `config.yaml` overrides. The session dependencies in `genesis_server/dependencies.py` handle this automatically. Tools receive the resolved connection string via `user_db_url` and `memory_db_url` kwargs.

---

## Full-Text Search

The memory database uses SQLite FTS5 for full-text search. The virtual table and sync triggers are set up in `genesis-core/src/genesis_core/persistent_memory/db.py`. Triggers keep the FTS index in sync with the real tables automatically on insert, update, and delete.

---

## Key Files

| File | Purpose |
|---|---|
| `genesis-core/src/genesis_core/configs.py` | `Config` with `db`, `user_db`, `memory_db` settings |
| `genesis-core/src/genesis_core/productivity/models.py` | `Task`, `Project`, `JournalEntry` models |
| `genesis-core/src/genesis_core/productivity/db.py` | Productivity engine and session |
| `genesis-core/src/genesis_core/productivity/service.py` | Productivity CRUD functions |
| `genesis-core/src/genesis_core/persistent_memory/models.py` | `EventLog`, `TopicalMemory` models |
| `genesis-core/src/genesis_core/persistent_memory/db.py` | Memory engine, session, FTS setup |
| `genesis-server/src/genesis_server/database.py` | System DB engine, init, admin seeding |
| `genesis-server/src/genesis_server/dependencies.py` | Session dependencies (`ProdSessionDep`, `MemorySessionDep`) |
| `genesis-server/src/genesis_server/models/user.py` | `User` model |
| `genesis-server/src/genesis_server/models/chat.py` | `ChatSession`, `ChatMessage` models |