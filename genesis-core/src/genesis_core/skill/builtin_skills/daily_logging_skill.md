---
name: "daily_logging_skill"
description: "Use this skill when user wants to log, add to log, or record that something happened during the day."
version: "1.0"
---

# Daily Logging Skill

This skill is triggered when user wants to "log", "add to log", or "record" that something happened.

**Procedure**:

- **Step 1**: figure out what to log. If user mentioned in their initial request, use it. Otherwise, ask user what they want to log
- **Step 2**: find and read the journal entry of today. If it does not exist, create it
- **Step 3**: find a log section in today's journal entry. If it does not exist, create a section for logging events and then move to the next step
- **Step 4**: add a log line to the journal entry with current datetime, and the information user wanted to log

Example log line: "16:48 - Finished a preliminary version of the long-horizon plan system"
