.PHONY: setup backend-lint backend-format backend-test type-check check-all check-all-backend help

# Target directories for Python logic
BACKEND_DIRS := genesis-cli genesis-core genesis-server genesis-tui genesis-tools src
FASTAPI_MAIN := genesis-server/src/genesis_server/main.py
FASTAPI_DIR := genesis-server/src/genesis_server/

# Directory for frontend
FRONTEND_DIR := genesis-frontend

# Shortcut for tools
UV := uv run
PNPM := cd $(FRONTEND_DIR) && pnpm

help: ## Show this help message
	@grep -E '^[-a-zA-Z_./]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

### Setup

setup-backend: ## Initial backend setup (uv sync)
	uv sync

setup-frontend: ## Initial frontend setup (pnpm install)
	$(PNPM) install

setup: setup-backend setup-frontend ## Initial setup for both backend and frontend

### Linting

lint-backend: ## Run Ruff linter on backend
	$(UV) ruff check $(BACKEND_DIRS)

lint-frontend: ## Run ESLint on frontend
	@echo "frontend linting disabled"

lint-fix-backend: ## Run Ruff linter on backend and fix all fixable problems
	$(UV) ruff check --fix $(BACKEND_DIRS)

lint: lint-backend lint-frontend ## Run all linters

### Format

format-backend: ## Auto-format backend code
	$(UV) ruff format $(BACKEND_DIRS)

### Type Check

type-check-backend: ## Run pyright type checker on backend
	$(UV) pyright $(BACKEND_DIRS)

type-check-frontend: ## Run TypeScript type checker on frontend
	$(PNPM) type-check

type-check: type-check-backend type-check-frontend ## Run all type checkers

### Test

test-backend: ## Run pytest across backend packages
	$(UV) pytest; exit_code=$$?; [ $$exit_code -eq 5 ] && exit 0 || exit $$exit_code

test-frontend: ## Run frontend tests
	$(PNPM) test:run

test: test-backend test-frontend ## Run all tests

### Run all code quality checks

check-all-backend: lint-backend type-check-backend test-backend ## Run all backend quality checks
check-all: lint type-check test ## Run all quality checks (lint + type check + test)

### Cleanup

clean-backend: ## Clean up cache and build artefacts of the backend
	rm -rf .pytest_cache .ruff_cache .pyright_cache .next
	find . -type d -name "__pycache__" -exec rm -rf {} +

clean-workspace-dir: ## Remove content of workspaces directory
	rm -rf workspaces/

clean-database: ## Remove content of workspaces directory
	rm -rf database/

clean-frontend: ## Clean up frontend
	cd $(FRONTEND_DIR) && rm -rf .next node_modules

clean: clean-workspace-dir clean-database clean-backend ## Clean up caches and build artifacts, workspaces, databases

### Build project (validates build without running)

build-frontend: ## Build frontend for production (fails on type/compile errors)
	$(PNPM) build

build-backend: ## Validate backend dependencies and lockfile
	uv sync --frozen

build: build-backend build-frontend ## Full production build validation

### Run project in dev mode (bare metal)

dev-backend: ### Run FastAPI backend in dev mode
	GENESIS__LOG_LEVEL=DEBUG $(UV) fastapi dev $(FASTAPI_MAIN) --reload-dir $(FASTAPI_DIR)

dev-frontend: ### Run frontend in dev mode
	$(PNPM) dev

dev: ### Run both backend and frontend in parallel in dev mode
	@$(MAKE) -j 2 dev-backend dev-frontend

### Run project in prod mode (bare metal)

run-backend: ### Run backend on bare metal
	$(UV) genesis serve

run-frontend: ### Run frontend on bare metal (build must be done first)
	$(PNPM) start

run: build ## Build (if needed) and run both in prod mode on bare metal
	@$(MAKE) -j 2 run-backend run-frontend

### Docker / Container Management

container/build: ## Build the Docker image
	docker compose build

container/pull: ## Pull the Docker image from registry
	docker compose pull

container/up: ## Run the project in a container in the background
	docker compose up -d

container/down: ## Stop and remove containers, networks
	docker compose down

container/down-volumes: ## Stop and remove containers, networks, and volumes
	docker compose down -v

container/restart: container/down container/up ## Restart containers

container/logs: ## Tail logs from the container
	docker compose logs -f

container/shell: ## Access the running container shell for debugging
	docker compose exec genesis-aio /bin/bash

container/rebuild: container/down container/build container/up ## Rebuild and restart containers

run-container: ## Build and run the project in a container (one command, foreground)
	docker compose up --build

stop-container: ## Stop the running containers
	docker compose stop

### Default target
.DEFAULT_GOAL := help
