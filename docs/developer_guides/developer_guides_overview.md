# Developer Guideline

This document provides instructions for developers and AI agents who try to add features, fix bugs, or adapt the codebase to different use cases and contexts.

-----

## How to run the code 

### Prerequisite to build and run the code

Machine running the dev build of this code should have the following software installed:

- `make`: for running the build and test scripts written in `Makefile`
- `uv`: for installing python, creating virtual environment, installing dependencies, and run the `python` backend of the project
- `node`, `pnpm`: for installing dependencies and run the frontend

If you want to use the application, you also need to have access to an LLM provider. The project was tested against the following providers:

- `openrouter`
- `minimax` coding plan
- `GLM` coding plan

Any OpenAI compatible endpoint would be compatible.

### Required configurations

You need to create an `.env` file at the repo root to configure the backend before you are able to start the code. You can copy the existing `.env.example` to get started.

In this configuration, you need to define an LLM provider and define a default LLM model. This would be used by the default LLM agent that is available to all users in the system.

``` bash
# Define the provider (openrouter)
myproject__providers__openrouter__name="openrouter"
myproject__providers__openrouter__base_url="https://openrouter.ai/api/v1"
myproject__providers__openrouter__api_key="sk1234"

# Define the model (let's name the key "default")
myproject__models__default__provider="openrouter"
myproject__models__default__model="nvidia/nemotron-3-nano-30b-a3b:free"
# Optional: add extra params
# myproject__models__default__params__temperature=0.5
```

For more details about configuration, see the docs [here](../architecture/modules/myproject-core/configuration.md)

### Commands

Use `make` if possible.

```bash
# First time setup
make setup

# One-time setup — installs the git hook scripts
uv run pre-commit install

# Run both backend and frontend in parallel (hot-reload enabled)
make dev

# Run backend only
make dev-backend

# Run frontend only
make dev-frontend
```


If you need to run python code against python backend, always use `uv`. Never use `python` or other python tools directly.

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

If you need to run command against frontend, always use `pnpm`.

```bash
# Correct
pnpm install
pnpm dev

# Avoid
npm install
npm run dev
```

-----

## How to test the code

### Design of QA System

The following tools are used for automated quality check and test of the codebase:

- `ruff`: linting backend
- `pyright`: type checking backend
- `eslint`: linting frontend 
- `tsc`: type checking and build frontend

This repository uses `pre-commit` hooks and `GitHub Action` to run tests automatically to ensure that master branch is healthy.


### Commands

```bash
# Run all hooks against all files
uv run pre-commit run --all-files

# Run against staged files only
uv run pre-commit run

# Run all checks: lint + type-check + test (both backend and frontend)
make check-all
```


-----

## How to build and release the code

### Release Artefacts and Processes

TBA

### Commands

TBA

-----

## Development Conventions

### Understand the architecture before code

Before implementing any new feature or bug fix, ensure that you understand the following thoroughly:

- Runtime architecture of the system: Runtime components, how they are deployed, how they connect with each other, and important data flows and control flows involving these components
- Module structure of the codebase: main modules making up the codebase of the system, their functionality, how runtime components are mapped onto code modules
- Tooling of the codebase: correct tools and commands to run and check the code

To understand the architecture, first check the architecture documentation. Then, read any source code module you consider necessary for your task to confirm the details of the code.

### Plan and articulate the plan before code

Always plan thoroughly before performing code changes. When you plan, you should always consider the following:

- Which runtime component(s) need to be added or modified to implement the new feature or bug fix?
- Which code module(s) would be impacted by the change you are going to make?
- Is there existing code module(s) you can import to implement your task or do you need to write new ones?
- If you need to implement new logic or module, would you be replicating some existing code? If that's the case, can you find a way to adapt the existing logic for your task instead? (See the DRY principle below)
- Do you need to add any configuration to the system to support your proposed change? If so, which are the configurations to add or modify, and how do you plan to implement it?
- What would be the side effect of your proposed change? Would your change break the existing, functional codebase?
- Is there any new tests you need to add to the codebase to test your proposed change?
- Do you need to update documentation to capture your proposed change?

For human developers and AI agents that review plans: it's your responsibility to ensure that the change does not violate the architectural design principles of the codebase.

### Don't Repeat Yourself (DRY)

Do not duplicate logic, module, UI components with your proposed code change.

Adapt your proposed new code to work with the existing logic, modules, components if possible.

Refactor existing logic, modules, components, into shared utilities if necessary. 

For example: imagine the codebase already have the logic for renewing authentication token, but this logic only works in the server action because it relies on setting browser sessions, therefore you cannot use it in your new edge component. Instead of writing a replica of logic to renew token in the edge component, you can: (1) refactor the token renew logic to a shared utility, (2) refactor the server action to call the utility to renew token, and then set the session, (3) write your edge component to use the utility to renew token, and then set the HTTP response header. With this design, the logic to renew token is not duplicated across the codebase.

### Keep It Simple

Do not add abstraction layers and modules to "future-proof" the project. If you are only going to add a new feature, do not add arbitrary abstract classes, abstract interfaces, complex inheritance chain for the sake of "clean code".

Your design need to prioritise readability and maintainability:

- Ensure that codes within each module contribute to a single functional unit or area of the code
- Split code modules only when this decision increases the cohesiveness and facilitate reuse of logic (DRY principle above)
- Use type (with typescript codebase) or schema (with python codebase) to standardize inputs, outputs, and commonly used data objects of module

### Don't Breaking Working Code

Assume that existing code not directly related to the proposed update or bug fix is functional. Avoid making change to existing components and modules.

For example: imagine you are trying to add horizontal scrolling to an existing complex, hierarchical component. It is desirable to modify code at the wrapper level around the component, rather than changing the code from inside the component, as you might not understand the prior design decisions and assumptions when this component was built.


### Master branch must past the QA Checks

Run code quality check command before starting to work on the codebase to notice any pre-existing issues.

Run code quality check command after finishing your code change, and fix any issues that are caused by your code change. Do not return the code for review before you have finished your quality check.

### No Partial Git Commit

Do not add or commit to git before or during your code change process. 

If you are an AI agent, this instruction applies to both you and your subagents.

### Human Developer Signing Off Commit

The final git commit implementing the feature or code change must be reviewed and signed off by a human developer, not AI agent.

### Document Your Change

Document any change to runtime and static architecture in the architecture docs directory.

If you change leads to any changes in the developer practice, update the developer guideline directory content.

### Dealing with type errors

When type errors occur, use judgment to determine whether they indicate a real bug or a tooling limitation:

- **Third-party library type errors** (e.g., SQLAlchemy, Pydantic, FastAPI) — If you're confident the code works but the type checker rejects third-party library functions, a targeted `// @ts-ignore` or `# type: ignore` is acceptable.
- **Our own type mismatches** — If the error is caused by mismatches against types or schemas **we define**, fix the type properly. Do not use `as any`, `as unknown`, or `type: ignore` to suppress errors from our own code.

-----

## Guide Index

Other topics covered in this developer guideline

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

- [Logging](logging.md) — How to add logs to your code and configure log levels
- [Testing](maintaining/testing.md) — Testing conventions and patterns
- [Documentation](maintaining/documentation.md) — How to write and maintain documentation

### Gotchas

- [Gotchas](./gotchas.md) - List of tricky bugs that we discovered and fixed in the past. Good to review to avoid making the same mistakes
