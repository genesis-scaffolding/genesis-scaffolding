---
name: "productivity_skill"
description: "Use this skill when user asks about tasks, projects, calendar, agenda, plans, journal entries, or requests to add, edit, or review tasks, projects, or journals."
version: "1.0"
---

# Productivity Skill

You have access to the user's productivity subsystem, which manages their tasks, projects, and journals. These belong to the user — you have read and write access to help the user stay organized.

## Data model

- **Projects** — High-level containers for related work. A project has a name, description, status, and deadline.
- **Tasks** — Individual units of work. They can either represent a to-do item or a calendar appointment.
    - A task has a title, description, status, assigned_date, hard_deadline, and can belong to multiple projects.
    - When a task is given a starting date and duration, it becomes an appointment, which appears on the user's calendar.
- **Journals** — Time-based entries for notes, reflections, or logs. A journal has a reference_date, entry_type, and content.
    - Daily journal contains user's daily goals and logs.
    - Weekly journal contains user's goals for a week. At the end of the week, progress and reflections regarding the whole week is written here.
    - Monthly journal: similar to weekly journal, but operating on the monthly scale.
    - Yearly journal: similar to weekly journal, but operating on the yearly scale.
    - Project journal: journal entry about arbitrary topic relevant to the project. For example, user might store the outline for a report to be written for a project here.
    - Misc. journal: anything else that does not belong to any of the category above.

Use the productivity tools (`search_tasks`, `read_task`, `create_task`, `update_tasks`, `search_projects`, `read_project`, `create_project`, `update_project`, `search_journals`, `read_journal`, `create_journal`, `edit_journal`) to help the user manage their work.

## How to search for tasks when user ask about or mention specific tasks or outcomes

1. Determine whether user's query aligns with any project. (e.g., if they ask what is left to buy for the house, and they have a project about house renovation, that project might be relevant)

2. List tasks from the relevant project.

3. Avoid searching across the task list unless it is really necessary to confirm that something does not exist.

4. In general, do not search journal entries when looking for tasks.

5. Respond to user after you have gathered all the necessary information.

## How to answer "what's left" or "agenda" questions

When the user asks what is left to do or agenda within a time period (this week, next month, etc.), they want to see the tasks. Follow these steps in order:

1. **Compute the date range first.** Use `compute_date_range` to get the exact start and end dates for the period. This removes all guesswork.
    - "this week" -> `compute_date_range(period="week", offset=0)`
    - "next week" -> `compute_date_range(period="week", offset=1)`
    - "this month" -> `compute_date_range(period="month", offset=0)`
    - "next month" -> `compute_date_range(period="month", offset=1)`
    - "last month" -> `compute_date_range(period="month", offset=-1)`
    - "this quarter" -> `compute_date_range(period="quarter", offset=0)`
    - "this year" -> `compute_date_range(period="year", offset=0)`
    - Adjust offset as needed for "the week after next" (+2), "two months ago" (-2), etc.

2. **Search for tasks.** Call `search_tasks` with:
    - `status`: `"todo"` or `"in_progress"` (only incomplete tasks)
    - `assigned_date_end`: the end date from step 1 (only the end date is needed — this fetches all incomplete tasks up to and including that date)
    - `deadline_end`: the end date from step 1 (only the end date is needed)
    - Use "OR" logic (default)
    - Leave the status to empty, so that incomplete tasks or appointments would be returned.

3. After receiving an overview of the tasks, respond to the user based on the information. If there is nothing, tell the user that you cannot find anything and finish the search.

## How to answer "what's on my calendar" questions

When the user asks what is on calendar within a time period (this week, next month, etc.), they want to see the calendar appointments (task with scheduled_start_date). Follow these steps in order:

1. **Compute the date range first.** Use `compute_date_range` to get the exact start and end dates for the period. This removes all guesswork.

2. **Search for calendar appointments.** Call `search_tasks` with:
    - Use both `scheduled_start_start` (from step 1) and `scheduled_start_end` (from step 1) to find appointments that start within the period.
    - Leave the status to empty, so that incomplete tasks or appointments would be returned.
    - Leave other fields empty.

3. After receiving an overview of appointments, respond to the user based on the information. If there is nothing, tell the user that you cannot find anything and finish the search.

## Key rules

- Always call `compute_date_range` first — do not try to calculate dates yourself.
- Dates are in YYYY-MM-DD format.
- Unless the user specifies a particular timeframe strictly, include tasks that fall within or before the timeframe (not just exactly within it).
- If the user says "what's left this week" on a Wednesday, include tasks assigned to earlier days of the same week that are still incomplete.
- Always confirm with the user before creating or updating productivity entities.
- Journal entries are personal — ask before creating or editing.