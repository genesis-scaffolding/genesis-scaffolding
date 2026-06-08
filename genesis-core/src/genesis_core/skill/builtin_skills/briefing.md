---
name: "briefing"
description: Prepare a daily briefing and create a fresh daily journal entry. Trigger when user asks for daily briefing, to prepare daily journal, help prepare for the day, or says "let's start the day"
version: "1.0"
---

## Daily Briefing & Journal Preparation

### Step 1 — Journal Scan

Search and read the following journal entries:

- Daily: today, yesterday, day before yesterday
- Weekly: this week, last week
- Monthly: this month, last month
- Yearly: this year

If any entry does not exist, skip it. Move on once all found entries are read.

### Step 2 — Task Fetch

Search tasks assigned Mon–Sun of the current week. This gives the week's planned workload plus any overdue items.

### Step 3 — Active Project Identification

1. Get all projects (overview level only).
2. Read the weekly and monthly journal entries. Identify which projects are in focus for this week based on what's written there.
3. Read the details of those active projects.
4. If no active project can be identified from the journals, skip this step.

### Step 4 — Briefing Presentation

Present everything conversationally. Do not use phrases like "according to the plan" or "as written in the journal." Instead, frame it as the user's own intention (e.g., "this week you planned to...", "for today your assigned tasks are...").

The briefing must include:

- Today's date
- Weekly goal and active project (or note if none is set)
- Today's assigned tasks plus overdue tasks — include task IDs inline for easy reference
- Upcoming deadlines
- Month-end reminder if near the end of the month

End by asking the user whether they want to proceed as planned or make adjustments.

### Step 5 — Adjustment Handling

Wait for the user's response. Possible outcomes:

- User asks for a project or day's task list → fetch and present
- User asks to add tasks to a project → create the tasks
- User asks to change task assigned dates → update them
- User approves → proceed to Step 6

### Step 6 — Journal Creation

Once the user approves, create a daily journal entry with the following three sections:

```
## Daily Goals

- [list of approved tasks with task IDs]

## Logs



## Reflection
```

- **Daily Goals**: list the approved tasks with their IDs
- **Logs**: leave empty for the user to fill throughout the day
- **Reflection**: leave empty for end-of-day debrief
