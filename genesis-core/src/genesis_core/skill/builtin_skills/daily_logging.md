---
name: "daily_logging"
description: Log events, activities, or notes into today's daily journal entry. Trigger when user asks to log, note down, or record something that happened today, or tells you they have just done something or had a meeting.

version: "1.0"
---

## Daily Logging

### Step 1 — Find or Create Today's Journal

Search for today's daily journal entry (reference_date = today). If it does not exist, create a new one using this template:

```
## Daily Goals

- [leave empty]

## Logs



## Reflection
```

### Step 2 — Determine What to Log

If the user provides the log content directly in their message, use it as-is.

If the user does not provide the exact wording, ask: "What would you like me to log?"

### Step 3 — Append to the Logs Section

Add the log as a **standalone paragraph** (not a bullet point). Each log entry stands on its own line.

If the log has sub-details, add them as bullet points beneath the paragraph.

Example log entries:

```
Started investigating a new technique for getting agents to write skills by demonstration. Completed one skill: "Daily Briefing & Journal Preparation" (#skill-daily-briefing.md)
```

or with sub-details:

```
Had a meeting with Joey to discuss course material scoping.
- He wants Module 1 expanded with more real-world examples
- Module 2-3 to follow the same demo repo pattern
```

### Step 4 — Done

No further action required. The log is saved.
