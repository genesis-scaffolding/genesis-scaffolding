# myproject-core

Shared Python library containing core application capabilities.

## Key Modules

- **Agent** — Loop execution, clipboard, prompts, memory
- **LLM Client** — Provider-agnostic interface (LiteLLM + Anthropic SDK)
- **Configuration** — Three-layer config loading, environment variables, user isolation
- **Productivity** — Tasks, Projects, Journals: models and service layer
- **Workflow** — Blackboard-pattern pipeline orchestration
- **Workspace** — Sandboxed filesystem for workflow jobs

## Documentation

See [docs/architecture/myproject-core/](docs/architecture/myproject-core/) for detailed architecture documentation.
