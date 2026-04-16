# Memory Tools

## Overview

Memory tools give the agent the ability to read, write, and manage its own persistent memory across chat sessions. There are two memory types: EventLog (append-only facts) and TopicalMemory (revisable knowledge with supersession chains).

## Available Tools

| Tool | Description |
|---|---|
| `remember_this` | Creates either an event or topic memory, consolidating creation logic |
| `search_memories` | Performs full-text search across all memories using FTS5 |
| `list_memories` | Browses memories with filters for type, tag, importance, and source |
| `get_memory` | Retrieves a specific memory by its ID |
| `update_memory` | Updates topic content, subject, or tags; for topics this triggers the supersession workflow |
| `delete_memory` | Removes a memory by ID |
| `rebuild_fts_index` | Rebuilds the full-text search index; administrative/maintenance tool |

## Two Memory Types

**EventLog** — An append-only chronological record of discrete facts. Events are never overwritten; they accumulate as a historical timeline. Fields: subject, event_time, content, tags, importance, source.

**TopicalMemory** — Revisable knowledge that accumulates and can be updated as new information arrives. When facts change, new revisions replace old ones while preserving the history via `superseded_by_id`. Fields: subject, content, tags, importance, source, superseded_by_id.

## Clipboard Integration

Memory entities are tracked in the agent's clipboard as `TrackedEntity` with item types `memory_event` and `memory_topic`. Live-sync each turn refreshes entity data from the database.

Memory tag hints (`memory_tag_hints`) and user profile content (`user_profile_content`) are refreshed every turn directly from the database — not subject to TTL decay.

## Tag Conventions

Tags are the agent's structured index of its own experience:

- **Format**: hyphen-connected words (e.g., `user-preference`, `boss-interaction`)
- **Soft taxonomy**: `user-*` (user profile, preferences), `observation-*` (directly observed events), `fact-*` (recorded facts)
- **Quantity**: 1-3 tags per memory — quality over quantity

## Related Modules

- `myproject_core.persistent_memory` — Memory database models, service layer, FTS5 search
- `myproject_core.tools.memory_tools` — All memory tool implementations
