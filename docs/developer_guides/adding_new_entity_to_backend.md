# Adding a New Data Entity

This guide describes how to add a new user-owned data entity to the backend. See the [Example: Adding a Source Entity](#example-adding-a-source-entity) section for a concrete walkthrough.

Before starting, read these references:
- [backend_architecture.md](../backend_architecture.md) — router pattern, DI system, startup lifecycle
- [database.md](../database.md) — SQLModel ORM, engine/session setup, subsystem structure
- [logging.md](../logging.md) — how to add logging to backend code

## Overview

Adding a new entity involves these steps:

1. Categorize the entity to decide where it belongs
2. Add SQLModel database models in `genesis-core`
3. Add Pydantic request/response schemas in `genesis-server`
4. Add REST API endpoints in `genesis-server`
5. Register the router in `main.py`

## Step 1: Categorize the Entity

Determine ownership to decide where data lives:

| Ownership | Examples | Storage | Session Dependency |
|---|---|---|---|
| System-wide | User accounts, chat sessions | Server DB | `get_session` |
| User-owned | Tasks, journals, sources | User DB | `get_productivity_session` or a new session |

User-owned entities follow the subsystem pattern: models in `genesis-core/<subsystem>/`, schemas and routes in `genesis-server`.

## Step 2: Add Database Models

### Create the subsystem directory

```
genesis-core/src/genesis_core/<entity_name>/
    __init__.py
    models.py
    db.py
    service.py
```

### Define the SQLModel in `models.py`

```python
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, JSON, MetaData
from sqlmodel import Field, SQLModel

_entity_metadata = MetaData()


def get_utc_now():
    return datetime.now(UTC)


class EntityName(SQLModel, table=True):
    metadata = _entity_metadata
    id: int | None = Field(default=None, primary_key=True)

    # Fields with index=True for frequently queried columns
    name: str = Field(index=True)
    status: str | None = None

    # JSON column for dict or list data
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Timezone-aware timestamps
    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True)),
    )
```

Key points:
- Use `Field(index=True)` on columns that are frequently queried
- Use `sa_column=Column(JSON)` for dict or list fields
- Define a dedicated `MetaData` to avoid collision with other subsystems
- Use a `StrEnum` for fields with a fixed set of values
- Define `get_utc_now()` for timezone-aware timestamps

### Set up engine and session in `db.py`

```python
from sqlalchemy import create_engine
from sqlmodel import Session

from ..configs import Config
from .models import _entity_metadata

_engines: dict[str, "Engine"] = {}


def get_engine(config: Config | None = None, db_url: str | None = None) -> "Engine":
    target_url = db_url or config.user_db.connection_string
    if target_url not in _engines:
        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
        )
        _entity_metadata.create_all(engine)
        _engines[target_url] = engine
    return _engines[target_url]


def get_session(config: Config) -> Session:
    engine = get_engine(config)
    with Session(engine) as session:
        yield session
```

## Step 3: Add Pydantic Schemas

Create schemas in `genesis-server/src/genesis_server/schemas/<entity_name>.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityNameCreate(BaseModel):
    name: str
    status: str | None = None


class EntityNameUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class EntityNameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str | None
    created_at: datetime
    updated_at: datetime
```

Key points:
- Three schemas: `Create` for POST, `Update` for PATCH, `Read` for responses
- `Read` uses `ConfigDict(from_attributes=True)` to allow reading from ORM objects
- `Create` and `Update` use optional fields (`str | None`) for PATCH compatibility
- Use `datetime` from Python standard library for timestamp fields

## Step 4: Add REST API Endpoints

Create the router at `genesis-server/src/genesis_server/routers/<entity_name>.py`:

```python
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from ..dependencies import ProdSessionDep
from ..schemas.<entity_name> import EntityNameCreate, EntityNameRead, EntityNameUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/<entity_name>", tags=["<entity_name>"])


@router.post("/", response_model=EntityNameRead, status_code=status.HTTP_201_CREATED)
def create_entity(data: EntityNameCreate, session: ProdSessionDep):
    from genesis_core.<entity_name>.models import EntityName

    db_entity = EntityName.model_validate(data)
    session.add(db_entity)
    session.commit()
    session.refresh(db_entity)
    return db_entity


@router.get("/", response_model=list[EntityNameRead])
def list_entities(session: ProdSessionDep):
    from genesis_core.<entity_name>.models import EntityName

    statement = select(EntityName)
    return session.exec(statement).all()


@router.get("/{entity_id}", response_model=EntityNameRead)
def get_entity(entity_id: int, session: ProdSessionDep):
    from genesis_core.<entity_name>.models import EntityName

    db_entity = session.get(EntityName, entity_id)
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return db_entity


@router.patch("/{entity_id}", response_model=EntityNameRead)
def update_entity(entity_id: int, data: EntityNameUpdate, session: ProdSessionDep):
    from genesis_core.<entity_name>.models import EntityName

    db_entity = session.get(EntityName, entity_id)
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    update_data = data.model_dump(exclude_unset=True, mode="python")
    for key, value in update_data.items():
        setattr(db_entity, key, value)

    db_entity.updated_at = datetime.now(UTC)
    session.add(db_entity)
    session.commit()
    session.refresh(db_entity)
    return db_entity


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: int, session: ProdSessionDep):
    from genesis_core.<entity_name>.models import EntityName

    db_entity = session.get(EntityName, entity_id)
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    session.delete(db_entity)
    session.commit()
```

### Standard endpoints to implement

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/entity_name` | Create a new entity |
| `GET` | `/entity_name` | List entities with optional filters |
| `GET` | `/entity_name/{id}` | Get a single entity by ID |
| `PATCH` | `/entity_name/{id}` | Partial update |
| `DELETE` | `/entity_name/{id}` | Delete an entity |

### On filtering and pagination

Add filter parameters as needed. For pagination:

```python
@router.get("/entity_name", response_model=PaginatedResponse)
def list_entities(session: ProdSessionDep, offset: int = 0, limit: int = 50):
    from genesis_core.<entity_name>.models import EntityName

    total = session.exec(select(EntityName)).all()
    items = session.exec(select(EntityName).offset(offset).limit(limit)).all()

    return PaginatedResponse(items=items, total=len(total), offset=offset, limit=limit)
```

## Step 5: Register the Router

Import and include the router in `genesis-server/src/genesis_server/main.py`:

```python
from .routers import (
    # ... existing imports
    entity_name,
)

app.include_router(entity_name.router)
```

## Files to Create

```
genesis-core/src/genesis_core/<entity_name>/
    __init__.py
    models.py       # SQLModel tables
    db.py           # engine and get_session

genesis-server/src/genesis_server/schemas/
    <entity_name>.py  # Pydantic Create/Update/Read schemas

genesis-server/src/genesis_server/routers/
    <entity_name>.py  # REST API endpoints
```

## Testing

Verify the new endpoints appear in Swagger UI at http://localhost:8000/docs. Use the interactive docs to test create, read, update, and delete operations. Check that responses match the expected schema and that the data persists across requests.

---

## Example: Adding a Source Entity

This section demonstrates the process described above by adding a "Source" entity — a document source to be tracked and used, for example, to build an agent-driven wiki.

### Step 1: Categorize

The Source entity is user-owned. It stores per-user document source records in the user's private database. Use `ProdSessionDep` as the session dependency.

### Step 2: Database Models

Create `genesis-core/src/genesis_core/sources/`:

**`__init__.py`**
```python
from .models import Source, SourceType

__all__ = ["Source", "SourceType"]
```

**`models.py`**
```python
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, JSON, MetaData
from sqlmodel import Field, SQLModel

sources_metadata = MetaData()


class SourceType(StrEnum):
    WEB = "web"
    FILE = "file"
    NOTE = "note"


def get_utc_now():
    return datetime.now(UTC)


class Source(SQLModel, table=True):
    metadata = sources_metadata
    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(index=True)
    url: str | None = None
    source_type: SourceType = Field(default=SourceType.WEB)
    description: str | None = None

    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True)),
    )
```

**`db.py`**
```python
from sqlalchemy import create_engine
from sqlmodel import Session

from ..configs import Config
from .models import sources_metadata

_engines: dict[str, "Engine"] = {}


def get_engine(config: Config | None = None, db_url: str | None = None) -> "Engine":
    target_url = db_url or config.user_db.connection_string
    if target_url not in _engines:
        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
        )
        sources_metadata.create_all(engine)
        _engines[target_url] = engine
    return _engines[target_url]


def get_session(config: Config) -> Session:
    engine = get_engine(config)
    with Session(engine) as session:
        yield session
```

### Step 3: Pydantic Schemas

Create `genesis-server/src/genesis_server/schemas/sources.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from genesis_core.sources.models import SourceType


class SourceCreate(BaseModel):
    name: str
    url: str | None = None
    source_type: SourceType = SourceType.WEB
    description: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    source_type: SourceType | None = None
    description: str | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str | None
    source_type: SourceType
    description: str | None
    created_at: datetime
    updated_at: datetime
```

### Step 4: REST API Endpoints

Create `genesis-server/src/genesis_server/routers/sources.py`:

```python
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from ..dependencies import ProdSessionDep
from ..schemas.sources import SourceCreate, SourceRead, SourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(data: SourceCreate, session: ProdSessionDep):
    from genesis_core.sources.models import Source

    db_source = Source.model_validate(data)
    session.add(db_source)
    session.commit()
    session.refresh(db_source)
    return db_source


@router.get("/", response_model=list[SourceRead])
def list_sources(session: ProdSessionDep, source_type: str | None = None):
    from genesis_core.sources.models import Source

    statement = select(Source)
    if source_type:
        statement = statement.where(Source.source_type == source_type)

    return session.exec(statement).all()


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: int, session: ProdSessionDep):
    from genesis_core.sources.models import Source

    db_source = session.get(Source, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    return db_source


@router.patch("/{source_id}", response_model=SourceRead)
def update_source(source_id: int, data: SourceUpdate, session: ProdSessionDep):
    from genesis_core.sources.models import Source

    db_source = session.get(Source, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = data.model_dump(exclude_unset=True, mode="python")
    for key, value in update_data.items():
        setattr(db_source, key, value)

    db_source.updated_at = datetime.now(UTC)
    session.add(db_source)
    session.commit()
    session.refresh(db_source)
    return db_source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: int, session: ProdSessionDep):
    from genesis_core.sources.models import Source

    db_source = session.get(Source, source_id)
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")

    session.delete(db_source)
    session.commit()
```

### Step 5: Register the Router

In `genesis-server/src/genesis_server/main.py`, add the import and include the router:

```python
from .routers import (
    # ... existing imports
    sources,
)

app.include_router(sources.router)
```

### Files Created

```
genesis-core/src/genesis_core/sources/
    __init__.py
    models.py
    db.py

genesis-server/src/genesis_server/schemas/
    sources.py

genesis-server/src/genesis_server/routers/
    sources.py
```