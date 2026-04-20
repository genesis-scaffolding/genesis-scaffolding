# Agent Prompts

## Overview

System prompts are assembled from modular fragments at agent initialization time. Rather than a single monolithic prompt string, the system uses a factory function that selects and concatenates fragments based on the agent's configuration — which tools it has access to, whether it has a memory database, whether it has a working directory, and so on.

This approach enables:

- **Version-controlled prompt parts** — each fragment can be updated independently
- **Conditional inclusion** — subsystems are only mentioned when relevant (e.g., memory guidance only when memory tools are present)
- **Clear ownership** — prompt content is co-located with the subsystem it describes
- **Composable construction** — adding a new tool category requires only a new fragment and a condition in the builder

## BuildPromptConfig

The factory function takes a `BuildPromptConfig` that encapsulates everything needed to construct the prompt:

- `system_prompt` — The agent-specific role block from the agent definition file
- `allowed_tools` — Tool names from agent configuration
- `interactive` — Whether the agent is in interactive mode
- `has_memory_db` — True when memory database is available
- `has_user_db` — True when productivity database is available
- `has_working_directory` — True when sandbox working directory is available

## build_system_prompt()

The factory function takes a `BuildPromptConfig` and returns a single string. The agent-specific `system_prompt` from the agent definition file is always appended last — it is the definitive role description and takes precedence over any generic guidance.

## Module Structure

The prompts module contains:

- **fragments.py** — All prompt fragment strings
- **builder.py** — `BuildPromptConfig` model and `build_system_prompt()` factory function

## Fragment Reference

Fragments are string constants. Each fragment is self-contained and includes the Markdown heading that appears in the final prompt.

| Fragment | Trigger | Purpose |
|----------|---------|---------|
| BASE_INSTRUCTION | Always | General instruction: pronoun conventions, clipboard concept |
| FRAGMENT_WORKING_DIRECTORY | has_working_directory or file tools | How to use file tools, read/write/edit patterns |
| FRAGMENT_MEMORY | Memory tools present | Memory as the agent's own faculty; EventLog vs TopicalMemory; tag conventions |
| FRAGMENT_PRODUCTIVITY_SYSTEM | has_user_db + productivity tools | Data model for tasks/projects/journals; tool names; principles |
| FRAGMENT_WEB_TOOLS | Web tools present | When to search vs fetch; citation expectations |
| FRAGMENT_PDF_TOOLS | PDF tool present | How to use pdf_to_markdown |

## Tag Conventions

Tags are framed as the agent's structured index of its own experience. Key conventions:

- **Format**: hyphen-connected words (e.g., user-preference, boss-interaction)
- **Soft taxonomy**: `user-*` (user profile, preferences), `observation-*` (directly observed events), `fact-*` (recorded facts)
- **Quantity**: 1-3 tags per memory — quality over quantity
- **User profile**: subject="user-profile", tag=["user-profile"], content as structured plain text

## Agent Initialization

At agent initialization, the monolithic `SYSTEM_PROMPT_PREFIX` constants have been removed. Instead:

1. `BuildPromptConfig` is constructed based on what capabilities the agent has
2. `build_system_prompt()` is called to produce the final string
3. The system_prompt string is used to initialize `AgentMemory` as the first system message

## Tool Category Detection

The builder uses frozen sets of tool names to detect which subsystems are active. Tool names are grouped into sets: `_MEMORY_TOOL_NAMES`, `_PRODUCTIVITY_TOOL_NAMES`, `_FILE_TOOL_NAMES`, etc. Inclusion logic uses set operations (`isdisjoint`) to determine which fragments to include.

## Old vs New

**Old approach** — monolithic prompt with if/else branches:

- No way to conditionally include memory guidance without also including file guidance
- All agents with tools got the same prompt regardless of which tools they actually had
- Prompt content mixed with agent initialization logic
- Impossible to version-control individual prompt sections independently

**New approach** — fragment-based factory:

- Only subsystems the agent actually has access to are mentioned in the prompt
- Prompt content organized by topic in fragments.py
- Builder is a pure function — testable in isolation
- Adding a new tool category requires adding a fragment and a condition, nothing else

## Key Design Decisions

1. **Agent role last** — The system_prompt from the agent definition file is always appended last so the agent definition takes precedence over generic guidance
2. **Non-interactive builder** — The builder is intentionally stateless — it produces a string and knows nothing about the agent loop
3. **Frozen sets for tool categories** — Tool detection uses frozenset.isdisjoint() which is fast and readable
4. **Soft taxonomy for tags** — The user-*/observation-*/fact-* taxonomy is suggested, not enforced — the agent has agency to create its own categories
5. **No TTL on rendered snapshots** — memory_tag_hints and user_profile_content in the clipboard are refreshed every turn and are not subject to TTL decay

## Related Modules

- `genesis_core.prompts` — Prompt fragment definitions (`fragments.py`) and factory function (`builder.py`)
