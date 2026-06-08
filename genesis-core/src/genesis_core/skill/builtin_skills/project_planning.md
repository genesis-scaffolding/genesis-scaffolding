---
name: "project_planning_skill"
description: Plan a new project or update an existing one. Trigger when user asks to plan a project, plan for achieving a certain outcome, or modify/update/add tasks or journal entries to an existing project.
version: "1.0"
---

## Project Planning & Update

### Pre-step — Project List Scan

Before doing anything, search and display all projects to get a bearing on current status. This helps identify if the requested project already exists.

---

## Part A — Determine the Target Project

**If the project is new:** Create a new project (see Part B).

**If the project already exists:** Confirm with the user which project they are referring to. Proceed to Part D.

---

## Part B — Creating a New Project

### Step 1 — Outcome Interview

Interview the user one question at a time to understand the desired outcome. Ask ~3 thoughtful questions covering:

- What business or purpose does this serve?
- What does "done" or "success" look like?
- Where is the starting position (existing assets, audience, infrastructure)?
- What is the timeline or deadline?

After 3 questions, ask: "Anything else you want to add or consider?" for free-form input.

### Step 2 — Confirm and Summarise

Present a summary of the gathered information and ask for confirmation. If the user has adjustments, work with them to refine until approved.

### Step 3 — Create the Project

Once approved, create the project with:

- **Name:** clear, outcome-oriented
- **Description:** capture purpose, starting position, strategy, timeline, and any nice-to-haves. Do NOT include dynamic data like deadlines, task IDs, or journal entry IDs.
- **Status:** `todo`

### Step 4 — Milestone & Deliverable Identification

Tell the user: "Let's plan for the project. First, let's think about milestones and deliverables."

Ask the user to brain-dump milestones and deliverables. Offer to provide recommendations if helpful.

Recommendations must be **actionable** — each milestone is a deliverable that can be marked done, not a vague ongoing state (e.g., "consistent posting rhythm" is not actionable; "publish 4 posts" is).

Ask up to 3 follow-up clarifying questions, one at a time. Only move on when the user approves the milestone list.

### Step 5 — Save Milestones to Journal

Once approved, create a project journal entry with:

- **Title:** `[Project Name]: Milestones & Deliverables`
- **Type:** `project`
- **Content:** list of approved milestones and deliverables
- **Reference date:** today's date

### Step 6 — Task Breakdown

Tell the user: "Now let's break these milestones into tasks."

For each milestone, recommend actionable tasks small enough to be done in 1–2 sessions (aim for 1 hour per session). Present the full task list and iterate with the user until they are satisfied and explicitly approve.

### Step 7 — Create Tasks

Once approved, create all tasks and link them to the project. Each task should have:

- A clear, actionable title
- A brief description if needed
- **Status:** `todo`

Notify the user when all tasks have been added and project planning is complete.

---

## Part C — Mid-Planning Pause

If planning must be paused and continued another day:

1. Update the project description to add a **handover note** at the top:

```
[PLANNING IN PROGRESS — DO NOT FINALISE]
- Planning started: [today's date]
- What has been decided: [summary of approved milestones and outcome]
- What has been done: [tasks identified so far, if any]
- Where to continue: [next step, e.g., "finish task breakdown for Milestone 3"]
After planning is complete, remove this note and clean up the description.
```

2. Update the project status to `in_progress` to signal active work.

---

## Part D — Updating an Existing Project

### Type 1: Add New Tasks

The user narrates items to add (e.g., as they walk through a house and see things to pack).

Confirm details if anything is unclear. Create the tasks and link them to the project. Notify the user when done.

### Type 2: Add Journal Entry

The user asks to note something down about the project (e.g., research findings, a report, meeting notes).

1. Search and review existing journal entries for this project.
2. If a relevant entry already exists, ask the user: "I found an existing journal entry about this. Do you want me to add to it, or create a new one?"
3. If nothing relevant exists, create a new project journal entry with the content.

### Type 3: Add New Milestone or Deliverable

1. Update the milestone journal entry to include the new milestone.
2. Go through the task breakdown process (Part B, Step 6) for the new milestone only.
3. Create the new tasks and link them to the project.

### Type 4: Adjust the Project Plan

The user says things have changed and the plan needs to be reworked.

1. Run the milestone identification process again (Part B, Step 4), using existing milestones as a starting point.
2. Run the task breakdown process again (Part B, Step 6).
3. Mark old tasks that are no longer relevant as `canceled`.
4. Update the milestone journal entry with the revised milestones.
5. Create new tasks as needed.
6. Clean up the project description (remove any handover notes if present).

### Type 5: Break Down a Task

The user asks to break down a specific task into smaller, more actionable subtasks.

1. Search for the task in the relevant project. If the task has a description, read it — the user may have already listed subtasks there.
2. Confirm the task with the user and show what was found (including any existing subtask list in the description).
3. Ask how they want to break it down. Offer recommendations if helpful.
4. Once the breakdown is gathered, present two options:
   - **Create new tasks** for each subtask, and cancel the original task
   - **Update the description** of the original task to document the subtasks (without creating new tasks)
5. Ask which option the user prefers and act accordingly.

---

## Completion

After planning is complete (new project or update), clean up the project description — remove any handover notes added during a mid-planning pause.
