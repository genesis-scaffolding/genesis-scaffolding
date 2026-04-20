# Playbook: Base Web App

**Use when:** The app needs a web UI backed by a FastAPI server. No agents, no workflows, no productivity features.

---

## What to Keep

### Backend
- `genesis-core/` — Core utilities, configs, schemas, LLM client (if you need it later)
- `genesis-server/` — FastAPI server, routers, auth, database models

### Frontend
- `genesis-frontend/` — NextJS app, pages, components, API client

### Remove
- `genesis-core/src/genesis_core/agent.py` and `agent_registry.py`
- `genesis-core/src/genesis_core/productivity/` — productivity models, service, DB
- `genesis-core/src/genesis_core/memory/` — memory subsystem
- `genesis-core/src/genesis_core/workflow_engine.py` and `genesis-core/src/genesis_core/workflow_registry.py`
- `genesis-core/src/genesis_core/workflow_tasks/`
- `genesis-core/src/genesis_core/workspace.py`
- `genesis-server/src/genesis_server/routers/productivity.py`
- `genesis-server/src/genesis_server/routers/agent.py`
- `genesis-server/src/genesis_server/routers/workflow.py`
- `genesis-server/src/genesis_server/sse/chatmanager.py`
- `genesis-tools/` — all tools
- `genesis-core/src/genesis_core/agents/` — all agent definitions

### Frontend — Remove
- Chat UI components and pages related to agents
- Workflow/job/schedule UI pages
- Productivity UI components (task, project, journal, calendar)

---

## Where to Add Code

### New Backend Entity
Follow the [Adding Entities](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-server%2Fadding-entities.md&type=code) guide.

Add models to `genesis-core/src/genesis_core/schemas.py` or a new module in `genesis-core/src/genesis_core/`.

Add routers to `genesis-server/src/genesis_server/routers/`. Register in `genesis-server/src/genesis_server/main.py`.

### New Frontend Page
Follow the [Frontend Pages](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-frontend%2Ffrontend-pages.md&type=code) guide.

Add to `genesis-frontend/app/`.

---

## What NOT to Do

- Do NOT create a new Python package outside of `genesis-core/` or `genesis-server/` for domain logic
- Do NOT create new registries or abstraction layers — add directly to existing routers and services
- Do NOT import from `genesis-tools/` or `genesis-core/agents/`

---

## Smoke Test

After adaptation:
```bash
uv run pyright .
cd genesis-frontend && pnpm build
```
