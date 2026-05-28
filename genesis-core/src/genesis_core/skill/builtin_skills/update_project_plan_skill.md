---
name: "update_project_plan_skill"
description: "Use this skill when user asks to modify, continue planning, adjust, or update an existing project plan. Triggered by phrases like 'modify the project plan', 'continue planning', 'adjust the project', 'update project tasks', or similar."
version: "1.0"
---

# Update Project Plan Skill

This skill is triggered when user asks to "modify", "continue planning", "adjust", or "update" an existing project plan.

## Update Project Plan Procedure

### Step 1: Read the existing project list

Use tool to read the existing project list if not available.

### Step 2: Find the project to update

Find the project to adjust based on user's request. Confirm your finding with user.

### Step 3: Bootstrap a new plan if needed

If the chosen project is just a placeholder with no project description and no task, switch to the `project_planning_skill` to help user bootstrap the project instead.

### Step 4: Ask user how they want to update

Ask user how they want to update the project plan. Options and corresponding actions:

- **Redo the project plan**: switch to `project_planning_skill`.
- **Add more milestones**: clarify the detail of the milestone with user, then add the milestone to the project description, and then help user brainstorm and break down the milestone into actionable tasks.
- **Add or adjust tasks under some milestones**: clarify the tasks to be added or changed, then update or add project tasks.
- **Other request**: let user specify what they want to change and follow their instruction. Always confirm with user before modifying the data.