---
name: "review_skill"
description: "Use this skill when user wants to run a review session or do a daily, nightly, weekly, monthly, or yearly review. Triggered by phrases like 'run a review session', 'do daily/nightly/weekly/monthly review', 'end of year review', or similar."
version: "1.0"
---

# Review Skill

This skill is triggered when user wants to "run a review session", "do a daily/nightly/weekly/monthly review", or "do an end of year review".

Review sessions capture user's progress toward goals and reflections in the corresponding journal entries. User can also make necessary adjustments to the plan.

## Review Procedure

### Step 1: Gather information with tools

Gather journals, tasks, and project list.

### Step 2: Determine review horizon based on user's request

If there is no concrete request, use the current date and time. There might be multiple review horizons. Confirm with user before moving on.

Example scenarios:
- If current time is evening or night, user likely wants to do daily review.
- If the date is Friday or weekends, user likely also wants to do weekly review.
- If the date is near the end of the month, user likely wants to do monthly review as well.
- If the date is near the end of the year, user likely wants to do yearly review as well.

### Step 3: Conduct interactive review session

Start from the lowest horizon identified in step 2. See the specific instructions below.

### Step 4: Continue with remaining horizons

Continue until all review horizons have been addressed.

## Daily Review

1. Search for assigned tasks completed today (`assigned_date = today AND status = completed`).
2. Remind user of their progress captured in the daily journal entry and from their task completion.
3. Ask user for any progress that has not been captured in the daily journal entry.
4. Ask user for any reflection they want to capture. Avoid asking directly "what is your reflection". Ask questions to stimulate user thinking. Let conversation flow naturally. Examples:
   - What do you think about your progress today?
   - What are three things you are proud of today?
   - What would be one thing you wish you had done differently?
   - What do you think you should focus on tomorrow?
5. Update the daily journal entry with the complete list of tasks completed today, any newly captured progress, and reflection. Add a subsection for reflection if it does not exist.
6. Add the summary of daily progress to the weekly journal entry. Add a subsection for progress recording in the weekly journal entry if it does not exist.

## Weekly Review

1. Remind user of their progress this week based on the weekly journal entry.
2. Try to gather from user the progress of missing days in the weekly journal entry.
3. Ask user for any reflection or plan that they want to capture. Avoid asking directly. Ask stimulating questions one by one. Examples:
   - What do you think about the progress this week?
   - What are the most proud outcome of this week?
   - What would you do differently next week?
   - Where should be the focus next week?
4. Update the weekly journal entry with any newly captured progress and reflection. Add a subsection for reflection if it does not exist.
5. Add the summary of weekly progress to the monthly journal entry. Add a subsection for progress if necessary.

## Monthly Review

1. Remind user of their progress this month based on the monthly journal entry.
2. Try to gather from user progress of any week not captured in the journal entry.
3. Ask user for reflection or plan they want to capture. Avoid asking directly. Ask stimulating questions one by one. Examples:
   - What do you think about the progress this month?
   - What are the most proud outcome?
   - Were the choice of projects suitable?
   - What should we do differently next month?
   - Where should be the focus next month?
4. Update the monthly journal entry with newly captured progress and reflection. Add subsection for reflection if necessary.
5. Add a summary of monthly progress to the yearly journal entry. Add a subsection for progress if necessary.

## Yearly Review

1. Remind user of their progress and achievement this year.
2. Ask user for any reflection or plan they want to capture. Avoid asking directly. Ask stimulating questions one by one. Examples:
   - What do you think about what you achieved this year?
   - Where do you think we should plan differently?
   - Where should we focus more next year?
3. Update the yearly journal entry with reflection. Add subsection for reflection if necessary.