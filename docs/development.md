# Development

See [AGENTS.md](../AGENTS.md) for additional guidelines.

## Prerequisites

You need the following installed on your machine:

- `make` — build and test scripts
- `uv` — Python package manager, virtual environment, and runtime
- `node` and `pnpm` — frontend dependencies

## First-Time Setup

```bash
git clone https://github.com/nguyentran0212/genesis-scaffolding
cd genesis-scaffolding

# Copy and edit environment configuration
cp .env.example .env
# Edit .env and set your LLM provider and default model

# Install all dependencies (Python + Node.js)
make setup

# Install git hook scripts (lint/type-check before commits)
uv run pre-commit install
```

## Running the Dev Build

```bash
make dev              # Run both backend and frontend in parallel
make dev-backend      # Backend only (FastAPI with hot-reload)
make dev-frontend     # Frontend only (Next.js with hot-reload)
```

Backend: http://localhost:8000/docs
Frontend: http://localhost:3000

## Testing

See [testing.md](./testing.md) for full conventions.

```bash
make test-backend     # pytest
make test-frontend    # vitest
make check-all        # lint + type-check + test (both sides)
```

## Docker

The project ships as a single Docker image (`genesis-aio`) containing both backend and frontend.

```bash
# Build the image
make container/build

# Run the container
make container/up

# Stop and remove
make container/down
```

The `Dockerfile` and `docker-compose.yml` at the repo root define the image.

## Specific Topics

For a full module map of the codebase, see [architecture.md](./architecture.md). For detailed module references, see [module_reference.md](./module_reference.md).

### Workflows

- [Workflow architecture](../docs/workflow_architecture.md) — how the workflow engine works
- [Writing workflow manifests](../docs/workflow_manifest.md) — define new workflows in YAML
- [Building workflow tasks](../docs/workflow_task.md) — create custom workflow step types

## Keeping the module reference current

When you add, remove, or move a module in this codebase, update [module_reference.md](./module_reference.md) to reflect the change. This file is the primary map for agents and developers to navigate the codebase — stale references break understandability for both human developers and AI agents.