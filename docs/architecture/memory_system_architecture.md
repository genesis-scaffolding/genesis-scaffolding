# Memory System Architecture

## Overview

The memory system gives the agent persistent memory across chat sessions. It stores two types of memories:

- **EventLog** — append-only log of discrete facts/moments in time. Never overwritten.
- **TopicalMemory** — revisable knowledge that accumulates and can be updated as new information arrives.

Both are stored in a per-user SQLite database (`memory/user_memory.db`) inside the user's `internal_state_dir`, separate from the productivity subsystem database.

---

## Storage

### Database Configuration

Each user has a private memory database at `{internal_state_dir}/memory/user_memory.db`.

The `Config` class in `myproject_core/configs.py` holds a `memory_db: DatabaseConfig` field:

```python
memory_db: DatabaseConfig = Field(
    default_factory=lambda: DatabaseConfig(db_name="memory/user_memory.db")
)
```

This is initialized in `get_config()` with:
- `db_directory = internal_state_dir / "memory"`
- Directory created via `mkdir(parents=True, exist_ok=True)`
- Connection string built as `sqlite:///{db_directory}/{db_name}`

### Database Engine

The engine is managed in `myproject_core/memory/db.py`:

```python
_memory_engines = {}  # Process-level cache

def get_memory_engine(config: Config | None = None, memory_db_url: str | None = None):
    target_url = memory_db_url or config.memory_db.connection_string
    if target_url not in _memory_engines:
        engine = create_engine(target_url, ...)
        memory_metadata.create_all(engine)  # Creates EventLog and TopicalMemory tables
        _setup_fts(engine)  # Creates FTS5 virtual table + triggers
        _memory_engines[target_url] = engine
    return _memory_engines[target_url]
```

### Table Structure

Two SQLModel tables defined in `myproject_core/memory/models.py`:

#### EventLog

```python
class EventLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject: str | None = Field(default=None, index=True)
    event_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    content: str = Field(nullable=False)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    importance: int = Field(default=3, ge=1, le=5)
    source: MemorySource = Field(default=MemorySource.AGENT_TOOL)
    related_memory_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
```

#### TopicalMemory

```python
class TopicalMemory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject: str | None = Field(default=None, index=True)
    content: str = Field(nullable=False)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    importance: int = Field(default=3, ge=1, le=5)
    source: MemorySource = Field(default=MemorySource.AGENT_TOOL)
    superseded_by_id: int | None = Field(default=None, foreign_key="topicalmemory.id")
    supersedes_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=get_utc_now, sa_column=Column(DateTime(timezone=True)))
```

Both use:
- `memory_metadata` (dedicated `MetaData` object, separate from productivity subsystem)
- `DateTime(timezone=True)` for timezone-aware timestamps
- `JSON` columns for tags and related IDs

---

## Full-Text Search (FTS5)

### Why FTS5

SQLite's FTS5 provides full-text search with:
- **Porter stemming** — "integration" and "integrate" both reduce to "integr" and match
- **BM25 ranking** — results ranked by relevance
- **Boolean operators** — `integration AND memory` or `integration OR memory`

### Virtual Table

An FTS5 virtual table is created in `db.py`:

```sql
CREATE VIRTUAL TABLE memory_fts USING fts5(
    id,
    table_type,      -- 'event' or 'topic'
    subject,
    content,
    superseded_by_id,
    tokenize='porter unicode61'
);
```

### Sync Triggers

Six triggers keep the FTS5 index in sync with the base tables:

```sql
-- EventLog
CREATE TRIGGER eventlog_ai AFTER INSERT ON eventlog
BEGIN INSERT INTO memory_fts(id, table_type, subject, content, superseded_by_id)
VALUES (new.id, 'event', new.subject, new.content, NULL); END;

CREATE TRIGGER eventlog_ad AFTER DELETE ON eventlog
BEGIN DELETE FROM memory_fts WHERE id = old.id AND table_type = 'event'; END;

CREATE TRIGGER eventlog_au AFTER UPDATE ON eventlog
BEGIN UPDATE memory_fts SET subject = new.subject, content = new.content
WHERE id = new.id AND table_type = 'event'; END;

-- TopicalMemory (includes superseded_by_id for filtering)
CREATE TRIGGER topicalmemory_ai AFTER INSERT ON topicalmemory ...
CREATE TRIGGER topicalmemory_ad AFTER DELETE ON topicalmemory ...
CREATE TRIGGER topicalmemory_au AFTER UPDATE ON topicalmemory ...
    SET superseded_by_id = new.superseded_by_id ...
```

### Search Query

```python
fts_sql = text("""
    SELECT id, table_type, bm25(memory_fts) as score
    FROM memory_fts
    WHERE memory_fts MATCH :query AND table_type = 'event' AND superseded_by_id IS NULL
    ORDER BY score
    LIMIT :limit
""")
```

The `MATCH` clause uses FTS5's default AND operator — all query terms must match. The porter tokenizer handles morphological variants automatically.

### Backfill

If the FTS5 index goes out of sync, `rebuild_fts_index(session)` clears and repopulates it:

```python
def rebuild_fts_index(session: Session) -> dict[str, int]:
    session.execute(text("DELETE FROM memory_fts"))
    session.commit()
    events = session.query(EventLog).all()  # Uses session.query() not session.exec()
    for e in events:
        session.execute(text("INSERT INTO memory_fts(...) VALUES (...)"), {...})
    ...
```

---

## Service Layer

Located in `myproject_core/memory/service.py`, the service layer provides CRUD operations and search.

### EventLog Operations

- `create_event_log(session, data)` — creates and returns new EventLog
- `get_event_log(session, event_id)` — retrieve by ID
- `list_event_logs(session, tag, importance, source, sort_by, order, limit, offset)` — list with filters
- `delete_event_log(session, event_id)` — delete by ID

### TopicalMemory Operations

- `create_topical_memory(session, data)` — creates new TopicalMemory
- `get_topical_memory(session, memory_id)` — retrieve by ID
- `list_topical_memories(session, superseded, tag, importance, source, sort_by, order, limit, offset)` — list with filters
- `update_topical_memory(session, memory_id, data)` — in-place update (for minor changes)
- `supersede_topical_memory(session, memory_id, new_content, ...)` — creates new revision, marks old as superseded
- `get_revision_chain(session, memory_id)` — walk superseded chain backwards
- `delete_topical_memory(session, memory_id)` — delete by ID

### Unified Search

- `search_memories(session, query, memory_type, limit)` — FTS5 full-text search across events and topics

### Session Query Style

> **Important:** The service layer uses `session.query(Model)` (SQLAlchemy's classic API) instead of `session.exec(select(Model))` (SQLModel's modern API). Testing showed that `session.exec()` returns `sqlalchemy.engine.row.Row` objects instead of mapped model instances after FTS5 DDL operations. `session.query(Model)` consistently returns proper model instances.

---

## Agent Tools

Located in `myproject_tools/memory_tools.py`, six tools expose memory operations to the agent:

| Tool | Description |
|------|-------------|
| `remember_this` | Create an event or topic memory |
| `search_memories` | Full-text search across memories |
| `list_memories` | Browse with filters (type, tag, importance, source, etc.) |
| `get_memory` | Retrieve specific memory by ID |
| `update_memory` | Update topic content/subject/tags (triggers supersession) |
| `delete_memory` | Delete a memory |
| `rebuild_fts_index` | Rebuild FTS5 index (admin/maintenance tool) |

All tools receive `memory_db_url` and call `get_memory_session(memory_db_url)` to obtain a database session.

---

## Agent Integration

### Registry Registration

In `myproject_tools/registry.py`:

```python
from .memory_tools import (
    DeleteMemoryTool, GetMemoryTool, ListMemoriesTool, RebuildFtsIndexTool,
    RememberThisTool, SearchMemoriesTool, UpdateMemoryTool,
)
tool_registry.register("remember_this", RememberThisTool)
tool_registry.register("search_memories", SearchMemoriesTool)
tool_registry.register("list_memories", ListMemoriesTool)
tool_registry.register("get_memory", GetMemoryTool)
tool_registry.register("update_memory", UpdateMemoryTool)
tool_registry.register("delete_memory", DeleteMemoryTool)
tool_registry.register("rebuild_fts_index", RebuildFtsIndexTool)
```

### Agent Initialization

In `myproject_core/agent.py`:

```python
self.memory_db_url = memory_db_url  # Connection string to user's private memory database
```

Tools receive `memory_db_url` in their `run()` method and use it to get a session.

### Clipboard Integration

Memory entities are tracked as `TrackedEntity` with `item_type` values:
- `memory_event`
- `memory_topic`

In `myproject_core/schemas.py`, `AgentClipboardPinnedEntity.item_type` and `pin_entity()` include these memory types.

In `myproject_core/agent_memory.py`, the `sync_memory_entities()` method handles memory entity live-sync.

---

## Clipboard TTL / Decay

The existing TTL/decay mechanism in `AgentClipboard.reduce_ttl()` handles memory entities automatically:

- Memory entities use the same `ttl` and `resolution` fields as productivity entities
- As TTL decreases: `detail` → `summary` → expired
- No changes needed to the clipboard subsystem

---

## Deferred to Future Versions

1. **Dream workflow** — nightly chat history summarisation job
2. **Importance scoring algorithm** — auto-assign importance 1-5 based on content analysis
3. **Related memory linking** — automatic linking of `related_memory_ids` based on topic/person/event
4. **LLM-assisted relevance scoring** — pluggable retrieval strategy layer

---

## Critical Files

| File | Purpose |
|------|---------|
| `myproject-core/src/myproject_core/configs.py` | `memory_db: DatabaseConfig` config field |
| `myproject-core/src/myproject_core/memory/models.py` | EventLog and TopicalMemory SQLModel classes |
| `myproject-core/src/myproject_core/memory/db.py` | Engine/session management, FTS5 setup |
| `myproject-core/src/myproject_core/memory/service.py` | CRUD operations, FTS5 search, backfill |
| `myproject-core/src/myproject_core/memory/__init__.py` | Module exports |
| `myproject-tools/src/myproject_tools/memory_tools.py` | 6 agent tools |
| `myproject-tools/src/myproject_tools/registry.py` | Tool registration |
| `myproject-tools/src/myproject_tools/schema.py` | `TrackedEntity` item_type additions |
| `myproject-core/src/myproject_core/schemas.py` | `AgentClipboardPinnedEntity` updates |
| `myproject-core/src/myproject_core/agent.py` | `memory_db_url` initialization |
| `myproject-core/src/myproject_core/agent_memory.py` | Memory entity sync |
| `myproject-core/src/myproject_core/agent_registry.py` | Passes `memory_db_url` to Agent |
