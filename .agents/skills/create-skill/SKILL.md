---
name: create-skill
description: >
  Create a new skill for the agent. Use when the user asks to "create a skill",
  "add a skill", or "write a skill". This skill handles creating new skills that
  guide the agent through specific tasks.
---

# Create Skill

Create a new skill to help the agent handle a specific type of task.

## What is a Skill?

A skill is a markdown file (`.agents/skills/<skill-name>/SKILL.md`) that instructs the agent on how to handle a recurring task. Skills are invoked when the user describes a task that matches the skill's trigger phrases.

In this project, most skills follow a simple pattern:
1. Read relevant documentation
2. Clarify requirements with the user
3. Create a plan and get approval
4. Implement
5. Verify

The documentation is the source of truth for technical details. The skill itself just guides the process.

## Workflow

### Step 1: Clarify Requirements

Ask the developer:
- What task does this skill handle?
- What trigger phrases should invoke this skill? (e.g., "Use when user asks to 'create X'")
- Is there existing documentation the agent should read for this skill?

### Step 2: Create Preliminary Design

Draft the skill structure:
- Skill name and trigger phrases
- Brief description of what it does
- Workflow steps

If documentation exists for this task, keep the skill concise. Reference the docs instead of duplicating details.

If no documentation exists, the skill may need more detailed instructions to guide the agent.

### Step 3: Iterate Until Approved

Refine based on developer feedback. Repeat until approved.

### Step 4: Implement

Write the skill file to `.agents/skills/<skill-name>/SKILL.md`.

After that, ask user to reload the agent harness for the skills to be detected.

## Reference

See existing skills in `.agents/skills/` for examples of the standard pattern:
- `create-workflow` - guides workflow creation
- `create-workflow-step` - guides workflow task creation
- `write-docs` - guides documentation writing
