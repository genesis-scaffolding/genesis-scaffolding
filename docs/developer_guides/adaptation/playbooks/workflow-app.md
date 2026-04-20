# Playbook: Workflow App

**Use when:** The app runs multi-step automated processes, scheduled or on-demand — with or without productivity features or agents.

This playbook is additive on top of the base web app. Apply [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) first, then apply this one.

---

## What to Keep

### Backend
- Everything from the base web app, plus:
- `genesis-core/src/genesis_core/workflow_engine.py`
- `genesis-core/src/genesis_core/workflow_registry.py`
- `genesis-core/src/genesis_core/workflow_tasks/` — workflow task types
- `genesis-core/src/genesis_core/workspace.py`
- `genesis-server/src/genesis_server/routers/workflow.py`
- `genesis-server/src/genesis_server/scheduler.py` — APScheduler for cron jobs

### Frontend
- Workflow, job, and schedule UI pages and components
- Execute workflow buttons and status displays

### Keep or Remove Depending on Need
| Subsystem | Keep when... | Remove when... |
|-----------|-------------|----------------|
| **Productivity** | App needs tasks/projects/journals | App is purely workflow-driven |
| **Memory** | Workflows need to remember context | Not needed |
| **Agents** | Workflows need to delegate to agents | Not needed |

---

## What to Remove

### If Only Workflows (No Productivity, No Agents)
- `genesis-core/src/genesis_core/productivity/`
- `genesis-server/src/genesis_server/routers/productivity.py`
- Productivity frontend components
- `genesis-core/src/genesis_core/agent.py` and `agent_registry.py`
- `genesis-core/src/genesis_core/memory/`
- `genesis-tools/`
- `genesis-core/src/genesis_core/agents/`
- `genesis-server/src/genesis_server/routers/agent.py`
- `genesis-server/src/genesis_server/sse/chatmanager.py`
- Agent and chat frontend components

### If Workflows + Productivity (No Agents)
- `genesis-core/src/genesis_core/agent.py` and `agent_registry.py`
- `genesis-core/src/genesis_core/memory/`
- `genesis-tools/`
- `genesis-core/src/genesis_core/agents/`
- `genesis-server/src/genesis_server/routers/agent.py`
- `genesis-server/src/genesis_server/sse/chatmanager.py`
- Agent and chat frontend components

---

## Where to Add Code

### New Workflow Task Type
Create a new file in `genesis-core/src/genesis_core/workflow_tasks/`.

Follow the pattern of existing task types (e.g., `base_task.py`, `file_read.py`).

Register the task type in `genesis-core/src/genesis_core/workflow_tasks/registry.py`.

### New Tool for Workflows
Tools used by workflow tasks go in `genesis-tools/`.

Follow the [Implementing Tools](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-agent%2Fimplementing-tools.md&type=code) guide.

### New Workflow Definition
Workflow manifests (`.yaml` files) go in `genesis-core/src/genesis_core/workflows/` or a user-managed directory configured in settings.

### Extend the Workflow Frontend
Add pages to `genesis-frontend/app/workflows/`.

---

## What NOT to Do

- Do NOT create a new "workflow runtime" — use `workflow_engine.py` as the orchestrator
- Do NOT create workflow tasks that duplicate what existing tasks do
- Do NOT add workflow logic directly in routers — keep tasks focused and composable
- All other restrictions from [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) apply

---

## Smoke Test

After adaptation:
```bash
uv run pyright .
cd genesis-frontend && pnpm build
```
