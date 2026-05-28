---
name: "long_horizon_planning_skill"
description: "Use this skill when user wants to make a plan, update a plan, or set goals for a week, month, year, or rest of the year. Triggered by phrases like 'make a plan', 'let's plan for this week/month/year', 'update the plan', or similar."
version: "1.0"
---

# Long-Horizon Planning Skill

This skill is triggered when user wants to "make a plan" or "update the plan" for a week, month, year, or rest of the year.

The goal is to link high-level distant goals to concrete actionable daily activities, so that user always has concrete things to do.

## Planning Horizons

The planning system has four horizons:

- **Yearly planning (end of year / beginning of a new year)**: identify high-level goals for the year and define projects necessary to achieve them. Results stored in the *yearly journal entry*. Projects are stored in the system.
- **Monthly planning (end of a month / beginning of a new month)**: determine subgoals from the yearly plan for the month. Select projects to work on this month. Results stored in the *monthly journal entry*.
- **Weekly planning (end of a week / beginning of a new week)**: determine week's goals based on monthly goals, assign project tasks to week days to build a weekly time table. Results stored in the *weekly journal entry*. Schedule dates are assigned to tasks directly.
- **Daily planning (beginning of the day / at night)**: review and adjust scheduled tasks. Results stored in the *daily journal entry*.

## Planning Procedure

### Step 1: Gather information with tools

- Journals of the previous time frame (yesterday, last week, last month, last year), current time frame (today, this week, this month, this year), and the next time frame (tomorrow, next week, next month, next year). If a journal entry cannot be found, assume it was not created.
- Tasks with scheduled date or starting date (appointment) falling in the current week and next week.
- List of current projects.

### Step 2: Determine planning horizons based on user's request

If there is no concrete request, use the current time. Multiple horizons might be performed in the same session. Present the inferred planning horizons to user for confirmation before moving to next step.

Example scenarios:
- Current time is end of the week and month, and journal entries for next week and next month do not exist -> User likely wants to plan for next month and next week.
- Current time is in the middle of the week, and journal entries of current week and current month do not exist -> User likely missed the previous planning session and wants to catch up. Planning horizons are this month and this week.
- Current time is end of the year, and journal entries for next year do not exist -> User likely wants to plan for next year, next month, and first week of that month.
- The current yearly journal entry does not exist or contains only placeholder content -> User likely missed the yearly planning session and wants to plan for the year as well.

### Step 3: Perform an interactive planning session

Start from the highest horizon identified in step 2. See the specific instructions below.

### Step 4: Continue with remaining horizons

Continue until all planning horizons have been addressed.

## Dealing with Interruption

- If user wants to pause the planning (e.g., they do not have time to complete), write down a "handover" document in the corresponding journal entries with all findings and necessary instructions so that you and the user can resume the process later.
- If "handover" information is detected in the journal entry of a planning horizon, continue from there rather than starting the planning from scratch.

## Yearly Planning

1. Remind user of previous and current year's goals, if they exist. Notify if nothing exists.
2. Capture user's yearly goal by asking probing questions. Avoid asking directly "what is your goals this year". Ask one question at a time. Let the conversation flow naturally. Examples:
   - Is there any important life event you need to handle this year?
   - What are things you want to see happening by the end of this year?
   - What aspects of your life do you want to improve this year?
   - If you can organise your life into different responsibility areas, what would they be? What do you want to achieve in each area?
3. Confirm with user the identified yearly goals and adjust until user approves, then move to next step.
4. Ask user about any projects they need to start this year to achieve the yearly goals. Offer suggestions from current project list and any missing projects that should be created.
5. Confirm with user the identified projects.
6. Create or update the yearly journal entry relevant to the current planning horizon to capture the identified goals and projects.
7. Create any missing projects.

## Monthly Planning

1. Remind user of current year's goals and projects, previous and current month's goals, previous and current week's goals and progress, and current focused project, if they exist.
2. Capture user's monthly goal. Avoid asking directly "what is your goals this month". Instead, offer suggestions based on yearly goals and progress of last months along those goals. Also allow user to specify completely new monthly goals (not part of existing yearly goals) if they want.
3. Confirm with user the identified monthly goals and adjust until user approves, then move to next step.
4. Ask user about the projects they want to work on this month. Offer suggestions based on current project list and yearly goals.
5. Confirm with user the selected projects.
6. Create or update the monthly journal entry relevant to the current planning horizon to capture the identified goals and projects.
7. Create any missing projects.
8. Offer to update the yearly goal to add any new goals outside the existing yearly goal. Make the update if user allows.

## Weekly Planning

1. Remind user of previous week's goals and progress, current month's goals and progress, current year's goals, time table (scheduled tasks and appointments) of the current week, and any deadlines or appointments falling within the current and next week, if they exist.
2. Capture user's weekly goal. Avoid asking directly "what is your goals this week". Instead, suggest based on monthly goals and progress in the last week. Also allow user to specify completely new goals if they want.
3. Confirm the weekly goals and adjust until user approves, then move to next step.
4. Confirm with user the project they want to work on this week, based on the focus project of the month.
5. Identify potential weekly tasks from existing projects, upcoming deadlines and appointments, and present to user.
6. Suggest a time table for the week:
   - Work tasks are between Monday and Friday.
   - Personal tasks and hobbies can be any day of the week, particularly weekends.
   - Do NOT move calendar appointments and tasks with deadlines.
7. Iterate and refine the time table with user until they approve, then move to next step.
8. Create a weekly journal entry to capture the weekly goals.
9. Update the assigned date of the identified tasks in Step 5 according to the time table finished in Step 7.

## Daily Planning

1. Remind user of their time table (scheduled tasks) today, any overdue tasks (tasks scheduled in the past but not completed), any incoming deadlines or appointments, and current weekly goals.
2. Ask if user wants to reschedule any task and modify the schedule date accordingly.