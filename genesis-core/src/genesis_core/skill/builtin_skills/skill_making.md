---
name: skill_making
description: Build a new skill by walking through a task together with the user step by step, then consolidate the process into a skill markdown file. Trigger when the user says "let's build a skill", "I want to document a skill for X", "let's revamp a skill", or similar.

---

## Skill Making by Demonstration

### Step 1 — Skill Scope & Trigger

The user explains what the skill does and when it should be triggered. Listen carefully — the user will describe the trigger conditions and the general purpose of the skill. Do not move on until the scope is clear.

### Step 2 — Walk Through the Task

The user walks you through the task step by step. For each step:

- Listen to the user's instruction
- Execute the step using the appropriate tools
- Wait for confirmation or the next instruction before moving on
- If something is unclear, ask — do not guess

Repeat until the user explicitly says the task is complete.

### Step 3 — Consolidation

Once the task is done, the user will tell you to write the skill doc. Before writing, confirm your understanding of the skill:

- What does the skill do?
- When does it trigger?
- What are the key steps?

Write the skill as a markdown file using this template:

```markdown
---
name: [skill-name]
description: [one-line description of what the skill does and when it triggers]
---

## [Skill Title]

### Step 1 — [Name of step]

[Description of what to do in this step. Be specific. Include tool calls if needed.]

### Step 2 — [Name of step]

[Description...]

[Continue for all steps...]
```

Save the file to the working directory and notify the user when done.

### Step 4 — Done

The skill file is in the working directory, ready to be copied into the skill system.
