# Developer Guides

## Overview

These guides cover the processes and conventions for extending and maintaining the Genesis Scaffolding application.

## Guide Index

### Extending the Server

- [Adding Entities](extending-the-server/adding-entities.md) — How to add new database entities and FastAPI routers to the backend
- [Adding Configuration](extending-the-server/adding-configuration.md) — How to add new configuration options to the system
- [Implementing Tools](extending-the-agent/implementing-tools.md) — How to implement a new agent tool and register it with the ToolRegistry

### Extending the Agent

- [Writing Agents](extending-the-agent/writing-agents.md) — How to create a new agent by writing a Markdown file with YAML frontmatter

### Adapting the Scaffolding

- [Adaptation Overview](adaptation/README.md) — Overview of adapting the scaffolding for different application types
- [Decision Process](adaptation/decision-process.md) — How to select the right extensions and plan the adaptation
- [Principles](adaptation/principles.md) — Core principles to follow when modifying the scaffold
- [Playbooks](adaptation/) — Step-by-step checklists for each app type:
  - [Core Web App](adaptation/core-web-app.md) — Web UI only, no agents/workflows/productivity
  - [Productivity App](adaptation/playbooks/productivity-app.md) — Base + tasks, projects, journals
  - [Workflow App](adaptation/playbooks/workflow-app.md) — Base + automated processes, scheduling
  - [Full Agent App](adaptation/playbooks/full-agent-app.md) — Everything enabled

### Extending the Frontend

> **⚠️ Before modifying any frontend code, you must read the frontend guides below.** Breaking the page layout rules (server/client component boundaries, PageContainer placement, scrollbar rules) causes runtime errors and broken layouts. The guides exist specifically to prevent these mistakes.

- [Frontend Components](extending-the-frontend/frontend-components.md) — How to integrate new backend entities into the frontend UI
- [Frontend Pages](extending-the-frontend/frontend-pages.md) — Layout, sizing, scroll management, and page archetypes
- [Frontend Tables](extending-the-frontend/frontend-tables.md) — Data table patterns with TanStack Table

### Using Workflows

- [Workflow Guide](using-workflows/workflow-guide.md) — Writing YAML workflow manifests, invoking workflows programmatically
- [Scheduled Workflows](using-workflows/scheduled-workflows.md) — Creating cron-based workflow schedules

### Maintaining

- [Testing](maintaining/testing.md) — Testing conventions and patterns
- [Documentation](maintaining/documentation.md) — How to write and maintain documentation
- [Development Workflow](development-workflow.md) — Running the project, quality gates, pre-commit hooks, and CI

## Tooling

### Python Side

Always use `uv run python` (not bare `python`) when running Python scripts or commands. The project uses `uv` for package management and virtual environment handling — calling `python` directly may miss dependencies or use the wrong environment.

```bash
# Correct
uv run python scripts/some_script.py
uv run pytest ...
uv run pyright ...
uv run ruff ...

# Avoid
python scripts/some_script.py
pytest ...
pyright ...
ruff ...
```

### Frontend Side

Always use `pnpm` for anything related to the Node.js/frontend side. The project does not set up `npm` directly — `pnpm` is the installed package manager.

```bash
# Correct
pnpm install
pnpm dev

# Avoid
npm install
npm run dev
```

### The Makefile

The `Makefile` at the repository root is the **authoritative entry point** for running checks and development tasks. It is also the tool used by CI. Prefer `make` over calling `uv` or `pnpm` directly, especially in pre-commit and CI contexts — it ensures consistency.

```bash
make check-all      # lint + type-check + test (everything)
make check-all-backend  # backend only
make dev            # run both backend and frontend in dev mode
make build          # validate production build
```

You can also call `uv` and `pnpm` directly for more granular control (e.g., `uv run pytest`, `pnpm tsc --noEmit`).

### Tool Summary

| Area | Tool | Note |
|---|---|---|
| Python runtime | `uv run python` | Not bare `python` |
| Python packages | `uv` | uv handles venv and lock file |
| Frontend packages | `pnpm` | Not `npm` |
| Frontend dev | `pnpm dev` / `pnpm build` | Next.js via pnpm |
| Linting/Type | ruff, pyright, eslint | Configured per package |
| Quality gates | `make check-all-backend` | Used by CI — prefer over raw uv/pnpm calls |

### Handling Type Errors

When type errors occur, use judgment to determine whether they indicate a real bug or a tooling limitation:

- **Third-party library type errors** (e.g., SQLAlchemy, Pydantic, FastAPI) — If you're confident the code works but the type checker rejects third-party library functions, a targeted `// @ts-ignore` or `# type: ignore` is acceptable.

- **Our own type mismatches** — If the error is caused by mismatches against types or schemas **we define**, fix the type properly. Do not use `as any`, `as unknown`, or `type: ignore` to suppress errors from our own code.
