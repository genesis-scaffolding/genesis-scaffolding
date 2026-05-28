---
name: adapt-scaffolding
description: >
  Adapt the scaffolding to serve a different use case. Use when the user asks to
  "adapt the scaffolding", "customise the scaffolding", "adapt for a new use case",
  "build on top of the scaffolding", or similar. This skill guides the agent through
  understanding the user's vision, planning the changes, and implementing them step
  by step in a feature branch.
---

# Adapt Scaffolding

Adapt the scaffolding to serve a different use case by extending the existing
monorepo structure with new agents, tools, workflows, entities, and frontend changes.

## Workflow

### Step 1: Read the Adaptation Guide

Before doing anything else, load `docs/developer_guides/adapting_scaffolding.md` to understand
the three-phase adaptation process (application vision, backend changes, frontend changes).

The adaptation guide is the source of truth for the overall process. This skill
guides the agent through following that process.

### Step 2: Gather the User's Vision

Engage with the user to understand what they want to build. Ask:

- **What does the application do?** Describe the user-facing purpose at a high level
- **Who uses it?** How does the user interact with it day-to-day?
- **What are the key agentic workflows?** Which processes should run automatically or on demand?
- **What data does it manage?** Are there new types of structured data to store?
- **What capabilities does the agent need?** New tools, distinct personas, or both?

Do not ask about implementation details yet. Focus on understanding the application
goal before discussing how to build it.

### Step 3: Identify the Required Changes

Based on the user's vision and the adaptation guide, list the changes needed across
the board. Categorise them by phase:

**Phase 2 (Backend)**:
- New workflows?
- New workflow step types?
- New agent manifests?
- New tools?
- New data entities?

**Phase 3 (Frontend)**:
- New pages?
- New navigation items?
- Homepage changes?
- Workflow access points?
- Quick action changes?

Present the full list to the user for review before proceeding.

### Step 4: Write the Adaptation Plan

After the user approves the list of changes, write the plan to `ADAPTATION_PLAN.md`
at the repository root. The plan should:

- List each change as a numbered item
- Group items by phase (Phase 2 backend, Phase 3 frontend)
- Include a brief description of what each item involves
- End with a checkbox section so items can be ticked off as they are completed

Present the plan to the user and wait for approval before proceeding.

### Step 5: Create a Feature Branch

Only after the plan is approved, create a new git branch for the adaptation work:

```bash
git checkout -b adapt/<short-description>
```

Use a descriptive but concise branch name. Keep all changes on this branch until
the work is complete and approved.

### Step 6: Implement Changes One at a Time

Work through the plan items in order. For each item:

1. Read the relevant developer guide for that change type before starting
2. Implement the change
3. Run `make check-all` to verify code quality (lint, type-check, tests)
4. Show the change to the user and confirm it meets the vision
5. If the user approves, tick off the item in the plan and commit the change
6. Move to the next item

Commit messages should reference the adaptation plan item. For example:
`feat(backend): add Model entity for model weight tracking (plan #3)`

Do not commit incomplete or unverified work. If a change requires multiple
smaller steps to complete, treat the whole change as one item and commit only
when the user has verified the complete feature.

### Step 7: User Verification

After all items are implemented, present the full set of changes to the user.
Let the user verify the adapted system end-to-end. Address any feedback or
adjustments the user requests.

### Step 8: Merge and Clean Up

Once the user gives full approval:

1. Merge the feature branch back into the main branch:
   ```bash
   git checkout main && git pull && git merge adapt/<branch-name>
   ```
2. Push the merged result
3. Delete the feature branch:
   ```bash
   git branch -d adapt/<branch-name>
   ```
4. Confirm the merge is complete with the user

If there are merge conflicts, resolve only conflicts in files you modified.
If a conflict is in a file you did not touch, ask the user for guidance.

## Reference

- Full adaptation process: `docs/developer_guides/adapting_scaffolding.md`
- Workflow guide: `docs/developer_guides/create_workflow.md`
- Workflow step guide: `docs/developer_guides/create_workflow_step.md`
- Agent manifest guide: `docs/developer_guides/creating_agent_manifests.md`
- Agent tool guide: `docs/developer_guides/creating_agent_tools.md`
- Backend entity guide: `docs/developer_guides/adding_new_entity_to_backend.md`
- Frontend entity guide: `docs/developer_guides/adding_frontend_entity.md`