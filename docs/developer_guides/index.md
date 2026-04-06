# Developer Guides

## Overview

These guides cover the processes and conventions for extending and maintaining the Genesis Scaffolding application.

## Guide Index

### Extending the Server

- [Adding Entities](extending-the-server/adding-entities.md) — How to add new database entities and FastAPI routers to the backend
- [Implementing Tools](extending-the-agent/implementing-tools.md) — How to implement a new agent tool and register it with the ToolRegistry

### Extending the Agent

- [Writing Agents](extending-the-agent/writing-agents.md) — How to create a new agent by writing a Markdown file with YAML frontmatter

### Extending the Frontend

- [Frontend Components](extending-the-frontend/frontend-components.md) — How to integrate new backend entities into the frontend UI
- [Frontend Pages](extending-the-frontend/frontend-pages.md) — Layout, sizing, scroll management, and page archetypes
- [Frontend Tables](extending-the-frontend/frontend-tables.md) — Data table patterns with TanStack Table

### Using Workflows

- [Workflow Guide](using-workflows/workflow-guide.md) — Writing YAML workflow manifests, invoking workflows programmatically
- [Scheduled Workflows](using-workflows/scheduled-workflows.md) — Creating cron-based workflow schedules

### Maintaining

- [Testing](maintaining/testing.md) — Testing conventions and patterns
- [Documentation](maintaining/documentation.md) — How to write and maintain documentation

## Tooling

### Python Side

Always use `uv run python` (not bare `python`) when running Python scripts or commands. The project uses `uv` for package management and virtual environment handling — calling `python` directly may miss dependencies or use the wrong environment.

```bash
# Correct
uv run python scripts/some_script.py

# Avoid
python scripts/some_script.py
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

### Tool Summary

| Area | Tool | Note |
|---|---|---|
| Python runtime | `uv run python` | Not bare `python` |
| Python packages | `uv` | uv handles venv and lock file |
| Frontend packages | `pnpm` | Not `npm` |
| Frontend dev | `pnpm dev` / `pnpm build` | Next.js via pnpm |
| Linting/Type | pyright, ruff, eslint | Configured per package |
