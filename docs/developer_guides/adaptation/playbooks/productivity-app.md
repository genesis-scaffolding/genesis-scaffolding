# Playbook: Productivity App

**Use when:** The app needs tasks, projects, journals, or calendar — with or without agents.

This playbook is additive on top of the base web app. Apply [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) first, then apply this one.

---

## What to Keep

### Backend
- Everything from the base web app, plus:
- `genesis-core/src/genesis_core/productivity/` — models, service, DB
- `genesis-server/src/genesis_server/routers/productivity.py`

### Frontend
- Everything from the base web app, plus:
- Productivity UI components (task table, project table, journal, calendar)
- Dashboard page with pinned productivity items

### Remove
- `genesis-core/src/genesis_core/agent.py` and `agent_registry.py`
- `genesis-core/src/genesis_core/memory/`
- `genesis-core/src/genesis_core/workflow_engine.py` and `genesis-core/src/genesis_core/workflow_registry.py`
- `genesis-core/src/genesis_core/workflow_tasks/`
- `genesis-core/src/genesis_core/workspace.py`
- `genesis-server/src/genesis_server/routers/agent.py`
- `genesis-server/src/genesis_server/routers/workflow.py`
- `genesis-server/src/genesis_server/sse/chatmanager.py`
- `genesis-tools/`
- `genesis-core/src/genesis_core/agents/`

### Frontend — Remove
- Chat UI components and pages related to agents
- Workflow/job/schedule UI pages

---

## Where to Add Code

### New Productivity Entity
Add models to `genesis-core/src/genesis_core/productivity/models.py`.

Add service methods to `genesis-core/src/genesis_core/productivity/service.py`.

Add router endpoints to `genesis-server/src/genesis_server/routers/productivity.py`.

### Extend the Productivity Frontend
Add components to the appropriate feature directory in `genesis-frontend/components/`.

---

## What NOT to Do

- Do NOT add productivity entities as agent tools — productivity is its own subsystem
- Do NOT create separate "productivity API client" packages — use the existing service layer
- All other restrictions from [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) apply

---

## Smoke Test

After adaptation:
```bash
uv run pyright .
cd genesis-frontend && pnpm build
```
