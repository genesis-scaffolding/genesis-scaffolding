# Using the Productivity Subsystem

This guide describes how to use the productivity subsystem for personal task and note management. It covers the philosophy behind the system, the workflow for capturing open loops, and the processes for planning and reviewing work at different time horizons.

For the technical design of the subsystem, see [productivity_subsystem.md](./productivity_subsystem.md).

## Overview

The productivity subsystem manages two types of information: things to do and things to remember. Things to do are stored as tasks and projects. Things to remember are stored as journal entries. This separation is intentional. A task is something you act on. A journal entry is something you read and reference. Projects bridge the two by representing outcome-level goals that generate actionable tasks.

The system supports a hierarchical planning approach: yearly goals -> monthly goals -> weekly focus -> daily tasks. It also supports a hierarchical work breakdown: project -> deliverables -> tasks. Together, these two hierarchies connect distant aspirations to concrete next actions.

## Capturing All Open Loops

Open loops are any commitments, ideas, or tasks sitting in your head that you have not yet captured and processed. The Getting Things Done (GTD) method calls these open loops. The key principle is: if it is in your head, it is not being managed. Capture everything, then decide what to do with it.

The productivity subsystem gives you three ways to capture open loops:

**Tasks.** Use a task when the open loop is an actionable item. Tasks can hold a title, description, deadline, scheduled date, and appointment time. They can be linked to projects or exist independently.

**Calendar appointments.** A task with a `scheduled_start` datetime becomes a calendar appointment. The time is stored in UTC and rendered in your local timezone. This distinguishes fixed commitments (appointments) from planned work sessions (assigned date).

**Projects.** Use a project when the open loop is a high-level outcome that cannot be completed in one session. A project does not need tasks at creation time. You can record that the project exists so you can return to it later and break it down. Projects also have a status field to track whether they are still active.

The workflow for capturing open loops is simple: when something comes to mind, add it immediately. A task title is enough. Details can be added later. Do not worry about structure or context when capturing. The structure comes later during planning and review.

## Hierarchical Work Breakdown

Once a project exists, the next step is to break it down. A project is a distant outcome. It cannot be acted on directly. It must be decomposed into concrete deliverables, and those deliverables must be decomposed into tasks.

The breakdown follows a two-level hierarchy:

**Project -> Deliverables.** A deliverable is a concrete piece of work you can point to and say "I delivered this." A project may have two or ten deliverables, depending on its scope. Deliverables are not separate entities in the system. They are recorded in a project journal entry during the planning session.

**Deliverables -> Tasks.** Each deliverable generates tasks. Tasks are actionable. Each task should be something you can complete in one session. If a task still feels too large, break it further.

**Capturing the breakdown.** When you sit down to plan a project, create a project journal entry first. Use the journal content to capture your thinking: the deliverables you identified, the rationale for the breakdown, any constraints or notes. This serves as a record of the planning process and can be referenced later.

After the breakdown, create the tasks and link them to the project. You can use the task list filtered by project to see the full breakdown at a glance.

## Hierarchical Planning Method

Planning answers the question "when do I do what?" The hierarchical planning method connects distant goals to daily actions through a sequence of planning sessions at different time horizons.

The key distinction is between **what to do** and **when to do it**. The work breakdown produces a list of actionable tasks. The hierarchical planning selects which tasks to focus on in a given period and schedules them. These are two separate decisions made at different times.

### Yearly Journal

Start with the yearly journal. Define your high-level goals for the year. These are the outcomes you want to achieve over twelve months. Goals should be directional and motivational, not detailed. For each goal, consider whether a project already exists to achieve it. If not, create one. You do not need tasks yet. The existence of the project is enough to remind you of the commitment.

You may also sketch out which quarters you want to focus on which goals. The yearly journal is primarily a capture of direction, not a schedule.

### Monthly Journal

Move to the monthly journal. Look at your yearly goals and select one or two to focus on this month. Create the monthly journal entry and record which yearly goals you are pursuing and why. Identify any projects that support those goals. Check the task lists of those projects and decide which tasks you want to tackle this month.

The monthly journal acts as a commitment layer between yearly direction and weekly execution.

### Weekly Journal

The weekly journal is where planning becomes concrete. Review the monthly goals and select the narrow set of tasks you will work on this week. Open the task list for each relevant project and assign `assigned_date` values to the tasks you want to work on. This creates a rough timetable for the week.

The weekly journal entry itself can capture your intentions: what you plan to accomplish, any dependencies or blockers, and notes about context or priorities. At this level, you are making scheduling decisions, not just capturing open loops.

### Daily Journal

Create a daily journal entry each morning. Review the tasks you scheduled for today. Adjust if needed — if yesterday's task did not get done, it either moves to today or gets rescheduled. If a new open loop appeared overnight, capture it as a task now.

The daily journal is less about planning from scratch and more about reviewing and adapting the weekly plan to the reality of the day.

## Review and Adjustment Cycle

Planning flows downward: yearly -> monthly -> weekly -> daily. Review flows upward: daily -> weekly -> monthly -> yearly. The review cycle ensures plans remain relevant and surfaces what actually happened versus what was intended.

### End of Day

Before ending the day, write in your daily journal. Record what you accomplished, what did not get done and why, any blockers encountered, and any new open loops that appeared. This is a short session. The goal is to close out the day and capture lessons while they are fresh.

### End of Week

At the end of the week, wrap up the weekly journal entry. Write a brief review: what went well, what did not, and what you are carrying forward to next week. Then create the journal entry for the next week, drawing from the monthly goals and the task lists.

The weekly review is also the time to check active projects. If a project has been idle for weeks and still has no tasks, consider whether it should be broken down now or if the commitment has faded.

### End of Month

At the end of the month, wrap up the monthly journal. Summarise progress toward the monthly goals, note what was completed, and assess what remains. Create the journal entry for the next month. Review the yearly goals to see if they still feel right. Adjust if the direction has shifted.

### End of Year

At the end of the year, wrap up the yearly journal. Write a retrospective on the year: what was achieved, what was not, and what you learned. Then create the journal entry for the next year.

## Putting It Together

The productivity subsystem works as an integrated system, not a collection of separate tools. The pieces connect:

- Open loops are captured as tasks or projects, never left in your head.
- Projects are broken down into tasks, with the breakdown captured in a project journal.
- Yearly, monthly, weekly, and daily journals provide the planning context that connects long-term goals to daily actions.
- Regular reviews keep the system accurate and the plans relevant.

Start small. Capture open loops as they appear. Create a project for any outcome that requires multiple sessions. Break projects down when you are ready to act. Use the journal types to plan and review at your preferred pace. The system adapts to how much structure you need.