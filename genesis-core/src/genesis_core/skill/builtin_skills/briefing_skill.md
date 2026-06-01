---
name: "briefing_skill"
description: "Use this skill when user asks for a briefing, agenda, status update, or what is on their plate for today, this week, this month, or this year. Triggered by phrases like briefing, agenda, what is on my plate, what do I have today, or similar."
version: "1.0"
---

# Briefing Skill

This skill is triggered when user asks for "briefing", "agenda", "what is on my plate", or similar status update for today, this week, this month, or this year.

## Briefing Procedure

### Step 1: Determine the time frame

Determine the time frame for the briefing (day, week, month, year) based on user request. If it cannot be found, default to daily briefing.

### Step 2: Gather information

Gather as much of the following as exists. Skip anything that cannot be found:
- Project list
- Daily journal entries: yesterday and today
- Weekly journal entry: current week
- Monthly journal entry: current month and next month
- Yearly journal entry: current year
- Tasks: assigned to this week, overdue tasks (assigned to previous days but not completed), incoming deadlines

### Step 3: Deliver the briefing

Deliver a briefing to user with the suitable information based on the type of briefing below.

## Daily Briefing

Present:
- Monthly and weekly goals
- Progress so far this week
- Assigned tasks for today and any overdue tasks
- Any upcoming deadlines

Offer to write down the briefing into a day overview section in the daily journal entry for user if the journal entry or such section does not exist.

## Weekly Briefing

Present:
- Yearly, monthly, and weekly goals
- Progress so far this month
- Assigned tasks of this week
- Any upcoming deadlines

If there is no timetable or weekly plan, direct user to the long-horizon planning skill.

## Monthly Briefing

Present:
- Yearly and monthly goals
- Progress so far this year
- Plan for this month