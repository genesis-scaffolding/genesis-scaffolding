# Agent Memory

## Overview

The memory system provides the agent with persistent memory that spans across chat sessions. Rather than starting each conversation fresh, the agent can recall past events, accumulated knowledge, and user preferences stored in prior interactions.

The system stores two distinct types of memories:

- **EventLog** — an append-only chronological record of discrete facts or moments in time. Events are never overwritten; they accumulate as a historical timeline.
- **TopicalMemory** — revisable knowledge that accumulates and can be updated as new information arrives. When facts change, new revisions replace old ones while preserving the history.

Both memory types reside in a per-user SQLite database located within the user's internal state directory, physically separated from the productivity subsystem database. This isolation ensures that memory operations do not interfere with productivity data and that each user maintains a private, independent memory store.

## Storage

Each user is provisioned a private memory database. The directory is created automatically on first access if it does not already exist.

Memory storage is implemented using SQLModel with two table definitions:

**EventLog Table**

EventLog is an append-only log designed for chronological record-keeping:

- `id` — unique identifier
- `subject` — indexed topic label for the event
- `event_time` — timezone-aware datetime marking when the event occurred
- `content` — the event description or fact
- `tags` — JSON array of string tags for categorization
- `importance` — integer rating from 1 to 5 indicating significance
- `source` — origin of the event (e.g., "user_statement", "system_inference")
- `related_memory_ids` — JSON array linking to related memory entries
- `created_at`, `updated_at` — timestamps with timezone awareness

**TopicalMemory Table**

TopicalMemory supports revision-based knowledge management:

- `id` — unique identifier
- `subject` — indexed topic label
- `content` — the knowledge or information stored
- `tags` — JSON array of string tags
- `importance` — integer rating from 1 to 5
- `source` — origin of the knowledge
- `superseded_by_id` — foreign key pointing to the newer revision that replaced this entry
- `supersedes_ids` — JSON array of IDs of entries this one superseded
- `created_at`, `updated_at` — timestamps with timezone awareness

Both tables use `DateTime(timezone=True)` for timestamp fields and JSON columns for tags and relationship tracking.

## Full-Text Search

SQLite's FTS5 (Full-Text Search version 5) module provides sophisticated text search capabilities across memory content.

**Porter Stemming** — The search system uses the Porter stemming algorithm, which reduces words to their root forms. This means that "integration" and "integrate" both reduce to the stem "integr" and will match each other in searches, improving recall without sacrificing precision.

**BM25 Ranking** — Results are ranked using the BM25 (Best Matching 25) algorithm, a probabilistic relevance ranking scheme that considers term frequency and document length normalization. More relevant results appear higher in the result set.

**Boolean Operators** — FTS5 supports boolean query syntax, allowing queries such as `integration AND memory` to find entries mentioning both terms, or `integration OR memory` to find entries mentioning either term.

An FTS5 virtual table is created with columns: `id`, `table_type` (distinguishing 'event' from 'topic'), `subject`, `content`, and `superseded_by_id`. The Porter tokenizer is applied to handle morphological variants.

**Trigger Synchronization** — Six database triggers maintain consistency between the FTS5 virtual table and the base tables. There are triggers for insert, update, and delete operations on both EventLog and TopicalMemory. When data changes in the base tables, the FTS5 index is automatically updated to reflect those changes.

**Index Rebuild** — If the FTS5 index becomes out of sync with the base tables (due to bulk operations, corruption, or other edge cases), a `rebuild_fts_index` operation clears the virtual table and repopulates it from the current base table contents.

## Service Layer

The service layer sits between the agent tools and the database, providing CRUD operations, search functionality, and higher-level memory management.

**EventLog Operations**

- `create_event_log` — creates a new EventLog entry and returns it
- `get_event_log` — retrieves a specific event by its ID
- `list_event_logs` — lists events with filtering by tag, importance, source, sort order, limit, and offset
- `delete_event_log` — removes an event by ID

**TopicalMemory Operations**

- `create_topical_memory` — creates a new knowledge entry
- `get_topical_memory` — retrieves a specific entry by ID
- `get_topical_memory_by_subject` — looks up the current (non-superseded) entry for a given subject; useful for checking if knowledge already exists before creating
- `list_topical_memories` — lists entries with the same filtering options as event logs
- `update_topical_memory` — performs an in-place content update for minor corrections
- `supersede_topical_memory` — creates a new revision, marks the old entry as superseded by the new one, and returns the fresh entry
- `get_revision_chain` — walks backwards through the superseded chain to retrieve all historical revisions of a topic
- `delete_topical_memory` — removes an entry by ID

**Tag Counting**

- `get_memory_tag_counts` — aggregates tag usage across all current (non-superseded) memories from both EventLog and TopicalMemory, returning a dictionary mapping each tag to its total count

**Unified Search**

- `search_memories` — executes an FTS5 full-text search query across both events and topics, returning combined results ranked by relevance

## Agent Integration

Seven agent tools expose memory operations to the language model, enabling the LLM to read, write, and manage memories during conversation:

- `remember_this` — creates either an event or topic memory, consolidating creation logic
- `search_memories` — performs full-text search across all memories using FTS5
- `list_memories` — browses memories with filters for type, tag, importance, and source
- `get_memory` — retrieves a specific memory by its ID
- `update_memory` — updates topic content, subject, or tags; for topic memories this triggers the supersession workflow
- `delete_memory` — removes a memory by ID
- `rebuild_fts_index` — rebuilds the full-text search index; intended as an administrative or maintenance tool

Memory entities are tracked in the agent's entity tracking system as `TrackedEntity` with item type values `memory_event` and `memory_topic`, allowing the agent to maintain awareness of memory state alongside other tracked entities.

## Clipboard Integration

Memory entities are live-synchronized to the clipboard each conversation turn, ensuring the agent has timely access to relevant memory information without requiring explicit retrieval calls.

Three synchronization operations manage memory data in the clipboard:

- `sync_memory_entities` — fetches pinned memory entities from the database and live-syncs them to the clipboard state
- `sync_memory_tag_hints` — queries the current tag counts across all memories and stores the result in `clipboard.memory_tag_hints`
- `sync_user_profile` — fetches the user profile topical memory entry and stores its rendered content in `clipboard.user_profile_content`

Both `sync_memory_tag_hints` and `sync_user_profile` are invoked every turn when the memory database is connected, ensuring this information remains current without relying on cached or stale data.

**Clipboard Fields for Memory**

- `memory_tag_hints` — a dictionary mapping each tag string to the count of current memories bearing that tag; refreshed every turn
- `user_profile_content` — a string containing the rendered user profile content, or `None` if no profile has been stored; this field never expires via TTL

## TTL and Decay

Pinned memory entities follow the same TTL and decay semantics as productivity entities. As the time-to-live decreases, the entity transitions through detail levels before expiring: detail → summary → expired.

In contrast, `memory_tag_hints` and `user_profile_content` are not subject to TTL or decay mechanisms. These fields are refreshed every turn directly from the database, acting as live query results rather than cached representations.

## Deferred to Future Versions

The following features are intentionally deferred and not part of the current architecture:

1. **Dream workflow** — a proposed nightly chat history summarization job that would process conversation logs while the user is inactive, extracting key facts and insights for memory storage
2. **Importance scoring algorithm** — automatic assignment of importance ratings (1-5) based on content analysis, removing the need for manual importance tagging
3. **Related memory linking** — automatic population of `related_memory_ids` based on detected topic, person, or event relationships between memories
4. **LLM-assisted relevance scoring** — a pluggable retrieval strategy layer that would use the language model to re-rank or filter search results beyond basic BM25 scoring

## Token Counting Interface

`AgentMemory` tracks token usage for context monitoring and display. Two fields and two methods form the public interface:

**Fields:**
- `history_tokens: int` — cached token count for the message history, updated by the agent
- `clipboard_tokens: int` — cached token count for the current clipboard, updated by the agent

**Methods:**
- `count_history_tokens(model: str) -> int` — counts tokens in `self.messages` using `count_tokens()` from the LLM client
- `count_clipboard_tokens(model: str) -> int` — renders the clipboard to markdown and counts tokens using `count_tokens()`

The counts are updated by the `Agent` at the end of each `step()` turn via `Agent.update_context_tokens()`. External consumers (e.g., the chat router) reconstruct an agent and call `get_context_info()` to retrieve the breakdown.

**`get_context_info()` return shape:**
```python
{
    "history_tokens": int,
    "clipboard_tokens": int,
    "total_tokens": int,
    "max_tokens": int,
    "percent": float,
}
```

## Related Modules

- `myproject_core.memory` — Memory database models, service layer, and FTS5 search implementation
- `myproject_core.prompts` — Memory-related prompt fragments (e.g., `FRAGMENT_MEMORY`)
- `myproject_core.llm.token_utils` — Token counting implementation
