---
name: "project_planning_skill"
description: "Use this skill when user wants to plan, make a plan, or break down a project or desired outcome into tasks and milestones. Triggered by phrases like 'plan this project', 'make a plan for X', 'break down this project', or similar."
version: "1.0"
---

# Project Planning Skill

This skill is triggered when user wants to "plan", "make a plan", or "break down" a project or desired outcome.

Project planning is the process of breaking down a project into tasks. A project represents a distant desirable outcome that needs multiple actions to achieve. Each action is captured by a task.

## Project Planning Procedure

### Step 1: Read the existing project list

Use the tool to read the existing project list.

### Step 2: Find or create the project

Find the project to plan based on user's request. Confirm your finding with user and move to Step 5. Otherwise, move to Step 3 to create a project.

### Step 3: Identify the desired outcome

Ask questions one by one to gather the following information:
- What is the desired outcome? Or is this an official work project assigned to the user?
- Are there any concrete deliverables to be made?
- Is there any known deadline for this project?

### Step 4: Create the project

Confirm with user the gathered information and then create the project in the system. Note the project id of the newly created project.

### Step 5: Identify milestones or deliverables

Identify any major milestones or deliverables of the project by asking the user. If there is nothing specific, suggest a way to break down the project into larger chunks. Present the breakdown and iterate with user to refine until user approves.

### Step 6: Break down milestones into tasks

For each chunk or milestone or deliverable, break it down into actionable tasks. Present the tasks and iterate with user until user approves. See the definition of actionable tasks below.

### Step 7: Confirm the breakdown

Confirm the breakdown of project into milestones and tasks with user and clearly present the list of tasks that would be created.

### Step 8: Update the project description

Update the project description with overview and major milestones or deliverables.

### Step 9: Create the tasks

Use tool to create the project's tasks. These tasks must be assigned to the project being planned (use the correct project id in the create task tool).

You can use tool to look up on the Internet for more insights before suggesting to the user how to break down an outcome into milestones and tasks, if you need more information than what is already in your training data.

## Variations

### Planning an existing project

If user wants to plan for an existing project, search for the existing project's tasks as well. Show user existing tasks and ask whether they want to add to these tasks or delete these tasks and start fresh. Do as they instruct.

### Pausing the planning

If user wants to pause the planning (e.g., they do not have time to complete), write down a "handover" document in the project description with all the findings so far and all necessary instructions so that you and the user can resume the process at a future time.

### Resuming from handover

If "handover" information is detected in the project description, continue from there rather than starting the project planning from scratch.

## What Is an Actionable Task

- A task describes a concrete action (e.g., write a section, create a script, inspect a property) rather than a vague aspiration (e.g., be a better person, work out more).
- A task is specific and small enough to finish in a few hours or at most a day (e.g., "write a subsection in methodology section" rather than "write the research paper").