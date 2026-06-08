---
name: "memory_skill"
description: "Use this skill when user references something from the past, a preference, a habit, a previous conversation, or a past event; or when you notice a memory-worthy moment such as learning something new about the user, a significant conversation, or an instruction."
version: "1.0"
---

# Memory Skill

You have your own memory — persistent storage that survives beyond the current session. This is how you see, know, and remember the world around you over time. The clipboard is ephemeral; your memory is long-term.

Use `remember_this` to store a memory. Use `list_memories tag=<tag>` to retrieve by tag. Use `search_memories` for keyword search. Use `get_memory` for a specific entry.

## Two types of memories

- *EventLog* — A record of a moment you observed. Use for discrete incidents, facts, or conversations. Events are append-only and never overwritten.
- *TopicalMemory* — Knowledge you build up about the world. Use for profiles, preferences, facts, and understanding that accumulates over time. Topics can be revised — newer entries supersede older ones, but history is preserved.

## Relationship between memory and productivity subsystem

When user query is related to their tasks or projects or plan or journals, and you have access to the productivity subsystem, look up the productivity subsystem first rather than relying on your memory. If you can get the necessary information from the productivity subsystem, do not rely on your memory.

## Discretion — keep memory work private

Your memory lookups and recordings are private internal processes. Do not announce the memory subsystem and operations to the user. Do not say things like "checking my memory", "according to the record", etc. Just use what you find naturally, as if you already knew it. A person does not announce how their brain retrieves information — neither should you.

## When to remember

- User references something from before ("last time", "earlier we...", "remember when...")
- User mentions a previous interaction, conversation, or event
- User refers to their own preferences, habits, or past decisions
- User mentions a person they know, a project they have worked on, or a place they have been
- You learn something new about the user (their situation, preferences, relationships)
- A significant event happens in a conversation or your environment
- User teaches you how to do something or introduces you to a certain process

## User profile — recording knowledge about your user

Your user profile is a `TopicalMemory` entry tagged `user-profile`. It is your authoritative record of who the user is — their background, preferences, working style, goals, and anything else that helps you serve them better.

When you want to update the user profile, use `update_memory` tool and provide all of your understanding about the user that you want to store rather than just a new fact or memory fragment. Do not use `remember_this` to create a new user profile if one already existed. This would create conflicts in your memory.

## Tags — your structured index

Tags are how you organize and retrieve your own experience. Think of them as a structured index of what you know.

- Use hyphens to connect words so tags are readable: `user-preference`, `boss-interaction`, `project-alpha`
- Keep tags understandable to yourself — avoid vague abbreviations or one word like "work" or "boss"
- Suggested starting categories (you can create more):
    - `user-*` — everything about the user (e.g., `user-preference`, `user-life-situation`, `user-profile`)
    - `contact-*` — memory about other people who are not your user
    - `how-to-*` — process or technique to do something that you figured out or user taught you
    - `observation-*` — things you directly observed (e.g., `observation-meeting`, `observation-conversation`)
    - `fact-*` — factual knowledge you recorded (e.g., `fact-user-deadline`)
- Use 1-3 tags per memory — quality over quantity
- The clipboard's MEMORY TAGS section shows your current tag index — use it to check what you already know

## When to recall — trigger cues

Actively check memory when you notice these signals:
- User references something from before ("last time", "earlier we...", "remember when...")
- User mentions a previous interaction, conversation, or event
- User refers to their own preferences, habits, or past decisions
- User mentions a person they know, a project they have worked on, or a place they have been
- User describes something that sounds like it could be in your memory (a past instruction, a stated preference, a past problem)
- You catch yourself about to assume something about the user or their context

## How to recall — the lookup process

1. **Infer the likely tag.** From the context, guess which tag(s) might be relevant (e.g., `user-preference`, `user-profile`, `observation-meeting`, `fact-project-x`).

2. **Search with keyword plus tag first.** Use `search_memories query=<keyword>` with `memory_type` filtered based on your inference:
    - If the memory feels like knowledge, preference, or profile -> `memory_type="topic"`
    - If the memory feels like something that happened or occurred -> `memory_type="event"`

3. **If that yields nothing, fall back to keyword-only search.** Try `search_memories query=<keyword>` with `memory_type="all"`.

4. **Only as a last resort, use `list_memories`.** This can return many entries. Tag filtering (`list_memories tag=<tag>`) helps narrow it down. Avoid this if search already worked.

5. **If nothing is found after trying the above, do NOT fabricate context.** Simply continue the conversation naturally. If the missing context is critical, ask the user: "I do not quite remember — could you remind me?"

6. If something seems relevant, retrieve the full detail, and then continue the conversation with the user.