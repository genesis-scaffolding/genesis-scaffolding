"""
Persistent memory subsystem manager for genesis_core.

Wraps the memory database (user_memory.db) and provides CRUD operations
for EventLog and TopicalMemory, plus full-text search.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from sqlmodel import col

from ..configs import Config
from ..persistent_memory.db import get_memory_engine
from ..persistent_memory.models import EventLog, MemorySource, TopicalMemory


class MemoryManager:
    """Manager for persistent memory subsystem (EventLog, TopicalMemory, FTS search)."""

    def __init__(self, config: Config):
        self.config = config
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = get_memory_engine(self.config)
        return self._engine

    def _session(self):
        from sqlmodel import Session as SQLSession
        return SQLSession(self._get_engine())

    # --- EVENT LOG ---

    def create_event_log(self, data: dict[str, Any]) -> EventLog:
        with self._session() as session:
            db_entry = EventLog.model_validate(data)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def get_event_log(self, event_id: int) -> EventLog | None:
        with self._session() as session:
            return session.get(EventLog, event_id)

    def list_event_logs(
        self,
        tag: str | None = None,
        importance: int | None = None,
        source: MemorySource | None = None,
        sort_by: Literal["event_time", "created_at", "importance"] = "event_time",
        order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[EventLog]:
        with self._session() as session:
            q = session.query(EventLog)
            if tag:
                from sqlalchemy import cast
                from sqlalchemy.types import String
                tag_pattern = f'%"{tag}"%'
                q = q.filter(cast(EventLog.tags, String).like(tag_pattern))
            if importance is not None:
                q = q.filter(col(EventLog.importance) == importance)
            if source is not None:
                q = q.filter(col(EventLog.source) == source)
            order_field = getattr(EventLog, sort_by)
            if order == "desc":
                q = q.order_by(order_field.desc())
            else:
                q = q.order_by(order_field.asc())
            return q.limit(limit).offset(offset).all()

    def delete_event_log(self, event_id: int) -> bool:
        with self._session() as session:
            entry = session.get(EventLog, event_id)
            if not entry:
                return False
            session.delete(entry)
            session.commit()
            return True

    def update_event_log(self, event_id: int, data: dict[str, Any]) -> EventLog | None:
        with self._session() as session:
            entry = session.get(EventLog, event_id)
            if not entry:
                return None
            for key, value in data.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    # --- TOPICAL MEMORY ---

    def create_topical_memory(self, data: dict[str, Any]) -> TopicalMemory:
        with self._session() as session:
            db_entry = TopicalMemory.model_validate(data)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def get_topical_memory(self, memory_id: int) -> TopicalMemory | None:
        with self._session() as session:
            return session.get(TopicalMemory, memory_id)

    def list_topical_memories(
        self,
        superseded: bool = False,
        tag: str | None = None,
        importance: int | None = None,
        source: MemorySource | None = None,
        sort_by: Literal["created_at", "updated_at", "importance"] = "updated_at",
        order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[TopicalMemory]:
        with self._session() as session:
            q = session.query(TopicalMemory)
            if superseded:
                q = q.filter(col(TopicalMemory.superseded_by_id).isnot(None))
            else:
                q = q.filter(col(TopicalMemory.superseded_by_id).is_(None))
            if tag:
                from sqlalchemy import cast
                from sqlalchemy.types import String
                tag_pattern = f'%"{tag}"%'
                q = q.filter(cast(TopicalMemory.tags, String).like(tag_pattern))
            if importance is not None:
                q = q.filter(col(TopicalMemory.importance) == importance)
            if source is not None:
                q = q.filter(col(TopicalMemory.source) == source)
            order_field = getattr(TopicalMemory, sort_by)
            if order == "desc":
                q = q.order_by(order_field.desc())
            else:
                q = q.order_by(order_field.asc())
            return q.limit(limit).offset(offset).all()

    def update_topical_memory(self, memory_id: int, data: dict[str, Any]) -> TopicalMemory | None:
        with self._session() as session:
            db_entry = session.get(TopicalMemory, memory_id)
            if not db_entry:
                return None
            for key, value in data.items():
                if hasattr(db_entry, key):
                    setattr(db_entry, key, value)
            db_entry.updated_at = datetime.now(UTC)
            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)
            return db_entry

    def supersede_topical_memory(
        self,
        memory_id: int,
        new_content: str,
        new_subject: str | None = None,
        new_tags: list[str] | None = None,
    ) -> TopicalMemory | None:
        with self._session() as session:
            old_entry = session.get(TopicalMemory, memory_id)
            if not old_entry:
                return None
            if old_entry.superseded_by_id is not None:
                return None

            new_entry = TopicalMemory(
                subject=new_subject if new_subject is not None else old_entry.subject,
                content=new_content,
                tags=new_tags if new_tags is not None else old_entry.tags,
                importance=old_entry.importance,
                source=MemorySource.AGENT_TOOL,
                superseded_by_id=None,
                supersedes_ids=[memory_id],
            )
            session.add(new_entry)
            session.flush()

            old_entry.superseded_by_id = new_entry.id
            session.add(old_entry)
            session.commit()
            session.refresh(new_entry)
            return new_entry

    def get_revision_chain(self, memory_id: int) -> list[TopicalMemory]:
        with self._session() as session:
            chain = []
            current_id = memory_id
            while current_id is not None:
                entry = session.get(TopicalMemory, current_id)
                if not entry:
                    break
                chain.append(entry)
                current_id = entry.superseded_by_id
            return chain

    def delete_topical_memory(self, memory_id: int) -> bool:
        with self._session() as session:
            entry = session.get(TopicalMemory, memory_id)
            if not entry:
                return False
            session.delete(entry)
            session.commit()
            return True

    # --- SEARCH ---

    def search_memories(
        self,
        query: str,
        memory_type: Literal["event", "topic", "all"] = "all",
        limit: int = 20,
    ) -> dict[str, list[EventLog | TopicalMemory]]:
        with self._session() as session:
            from sqlalchemy import text
            if not query.strip():
                return {"events": [], "topics": []}

            safe_query = self._escape_fts5_query(query)

            if memory_type == "event":
                type_filter = "table_type = 'event'"
                superseded_filter = "1=1"
            elif memory_type == "topic":
                type_filter = "table_type = 'topic'"
                superseded_filter = "superseded_by_id IS NULL"
            else:
                type_filter = "1=1"
                superseded_filter = "1=1"

            fts_sql = text(f"""
                SELECT id, table_type, bm25(memory_fts) as score
                FROM memory_fts
                WHERE memory_fts MATCH :query AND {type_filter} AND {superseded_filter}
                ORDER BY score
                LIMIT :limit
            """)
            fts_results = list(session.execute(fts_sql, {"query": safe_query, "limit": limit}).all())

            if not fts_results:
                return {"events": [], "topics": []}

            event_ids = [r.id for r in fts_results if r.table_type == "event"]
            topic_ids = [r.id for r in fts_results if r.table_type == "topic"]

            events = []
            topics = []
            if event_ids:
                events = list(session.query(EventLog).filter(col(EventLog.id).in_(event_ids)).all())
            if topic_ids:
                topics = list(session.query(TopicalMemory).filter(col(TopicalMemory.id).in_(topic_ids)).all())

            return {"events": events, "topics": topics}

    def get_memory_tag_counts(self) -> dict[str, int]:
        with self._session() as session:
            from sqlalchemy import text
            tag_counts: dict[str, int] = {}

            event_tag_sql = text("""
                SELECT value as tag
                FROM eventlog, json_each(eventlog.tags)
                WHERE eventlog.tags IS NOT NULL AND json_each.value IS NOT NULL
            """)
            for row in session.execute(event_tag_sql).all():
                tag = row.tag
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            topic_tag_sql = text("""
                SELECT value as tag
                FROM topicalmemory, json_each(topicalmemory.tags)
                WHERE topicalmemory.tags IS NOT NULL
                  AND json_each.value IS NOT NULL
                  AND topicalmemory.superseded_by_id IS NULL
            """)
            for row in session.execute(topic_tag_sql).all():
                tag = row.tag
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return tag_counts

    def get_user_profile(self) -> TopicalMemory | None:
        with self._session() as session:
            from sqlalchemy import text
            sql = text("""
                SELECT topicalmemory.id
                FROM topicalmemory, json_each(topicalmemory.tags)
                WHERE json_each.value = :tag
                  AND topicalmemory.superseded_by_id IS NULL
                ORDER BY topicalmemory.updated_at DESC
            """)
            ids = [row.id for row in session.execute(sql, {"tag": "user-profile"}).all()]
            if not ids:
                return None
            return session.get(TopicalMemory, ids[0])

    def get_topical_memory_by_subject(self, subject: str) -> TopicalMemory | None:
        with self._session() as session:
            return (
                session.query(TopicalMemory)
                .filter(col(TopicalMemory.subject) == subject)
                .filter(col(TopicalMemory.superseded_by_id).is_(None))
                .first()
            )

    # --- HELPERS ---

    @staticmethod
    def _escape_fts5_query(query: str) -> str:
        tokens = query.split()
        escaped_tokens = []
        for token in tokens:
            if "-" in token:
                token = token.replace("-", " ")
            escaped_tokens.append(token)
        return " ".join(escaped_tokens)
