# Testing

## Overview

Testing conventions and patterns for the Genesis Scaffolding project.

## Backend Testing

The backend uses **pytest** for unit and integration tests.

### Running Backend Tests

```bash
# Run all backend tests (via Makefile — the CI-compatible way)
make test-backend

# Run all backend tests (direct)
uv run pytest

# Run tests for a specific package
uv run pytest genesis-core/tests/

# List tests without running
uv run pytest --collect-only
```

### Test Structure

Each Python package has a `tests/` directory co-located with the source:

```
genesis-core/tests/
├── __init__.py
└── example.test.py   # replace with real tests

genesis-server/tests/
genesis-tools/tests/
genesis-cli/tests/
genesis-tui/tests/
src/tests/
```

Test files follow the `*.test.py` naming pattern. Pytest is configured in the root `pyproject.toml` under `[tool.pytest.ini_options]`.

### Adding Tests

1. Create `*.test.py` files in the appropriate `tests/` directory
2. Import the code under test
3. Write test functions prefixed with `test_`

## Frontend Testing

The frontend uses **Vitest** and **React Testing Library** for component tests.

### Running Frontend Tests

```bash
# Via Makefile — the CI-compatible way
make test-frontend

# Direct (from genesis-frontend directory)
pnpm test          # watch mode
pnpm test:run     # single run
```

### Test Structure

```
genesis-frontend/
├── vitest.config.ts   # Vitest configuration
└── tests/
    └── example.test.ts  # replace with real tests
```

### Adding Tests

1. Create `*.test.ts` or `*.test.tsx` files (co-located with components or in `tests/`)
2. Use `@testing-library/react` for component rendering
3. Use `describe`, `it`, `expect` globals (configured via `globals: true` in vitest config)

## Integration Testing

End-to-end tests verify the full request/response cycle through both frontend and backend.

## Quality Gates

- **Pre-commit hooks** (`.pre-commit-config.yaml`) run ruff, pyright, and (where enabled) eslint on staged files. Frontend eslint is currently disabled due to legacy errors — use `make type-check-frontend` and `make build-frontend` to validate frontend code locally.
- **CI pipeline** (`.github/workflows/ci.yml`) runs lint, type-check, and test for both backend and frontend on every push/PR
- Both must pass before code is merged. Run `make check-all` locally to verify before pushing.
