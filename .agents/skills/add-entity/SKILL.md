---
name: add-entity
description: >
  Add a new data entity to the system end-to-end. Use when the user asks to
  "add an entity", "create a new entity", "add a new feature", or "add support for X".
  This skill walks through adding the entity to both the backend and the frontend.
---

# Add Entity

Add a new data entity to the system, end-to-end from backend to frontend.

## Prerequisites

Before starting, ensure you have a clear understanding of the entity:
- What fields does it have?
- Is it user-owned or system-wide?
- Does it need relationships to other entities?

## Workflow

### Step 1: Clarify Requirements

Ask the user to confirm:
- The entity name and its fields
- How it will be used (list a few use cases)
- Whether it is user-owned or system-wide

### Step 2: Read the Guides

Read both guides in full before starting implementation:

1. `docs/developer_guides/adding_new_entity_to_backend.md` — how to add backend models, schemas, and REST API endpoints
2. `docs/developer_guides/adding_frontend_entity.md` — how to add frontend types, server actions, pages, and components

The guides contain the detailed technical instructions. This skill orchestrates the process.

### Step 3: Implement the Backend

Follow `docs/developer_guides/adding_new_entity_to_backend.md` to:
1. Categorize the entity (user-owned or system-wide)
2. Add SQLModel database models in `genesis-core`
3. Add Pydantic schemas in `genesis-server`
4. Add REST API endpoints in `genesis-server`
5. Register the router in `main.py`

Run `make check-all` to verify the backend passes all checks.

### Step 4: Implement the Frontend

Follow `docs/developer_guides/adding_frontend_entity.md` to:
1. Define TypeScript types in `genesis-frontend/types/`
2. Create server actions in `genesis-frontend/app/actions/`
3. Create pages under `genesis-frontend/app/dashboard/<entity_name>/`
4. Create components under `genesis-frontend/components/dashboard/<entity_name>/`
5. Add the navigation link in `app/dashboard/layout.tsx`

Run `pnpm check` (or the appropriate frontend check command) to verify the frontend passes all checks.

### Step 5: Verify End-to-End

After both backend and frontend are implemented:
1. Start the dev servers (`make dev`)
2. Test the CRUD operations via Swagger UI at http://localhost:8000/docs
3. Test the frontend pages in the browser
4. Ensure data created via the API appears in the frontend and vice versa

### Step 6: Report

Report to the user:
- Files created or modified
- Any deviations from the guides (and why)
- How to test the new entity

