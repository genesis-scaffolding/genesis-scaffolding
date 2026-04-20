# Logging Guide

## Overview

The application uses Python's standard `logging` module. Configuration is centralized in `genesis_core/logging_config.py` and controlled via the `Config` system, making it the single source of truth for all log levels.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Entry Points (configure once)                       │
│  • FastAPI server startup (main.py)                  │
│  • CLI main                                         │
│  • Direct script execution                          │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ genesis_core/logging_config.py                    │
│  setup_logging() → sets root logger level           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ All modules use hierarchical loggers                 │
│  logging.getLogger(__name__)                        │
└─────────────────────────────────────────────────────┘
```

### Key Principles

1. **Libraries don't configure logging** — they only use loggers
2. **Configure once at entry point** — `setup_logging()` is called before any other imports that might use logging
3. **Hierarchical loggers** — child loggers inherit from parents, so setting level on root affects all

## Adding Logs to Your Code

### 1. Get a logger

```python
import logging

logger = logging.getLogger(__name__)
```

Using `__name__` gives you automatic hierarchy. For example, in `genesis_server/routers/chat.py`, the logger name is `genesis_server.routers.chat`.

### 2. Use the right log level

| Level | When to use |
|-------|-------------|
| DEBUG | Dev details, loop iterations, variable states |
| INFO | Significant milestones, successful operations |
| WARNING | Recoverable issues, degraded behavior |
| ERROR | Operation failed, but the app continues |
| CRITICAL | App is unusable, will exit |

### 3. Use %-formatting (not f-strings)

```python
# Correct — lazy evaluation, only formats if log level is enabled
logger.debug("Loading agent %s from %s", agent_id, path)
logger.info("Agent %s loaded successfully", agent_id)

# Wrong — always formats even when logging is disabled
logger.debug(f"Loading agent {agent_id} from {path}")
```

### 4. Include context for errors

```python
logger.error("Failed to load agent %s: %s", agent_id, exc)
logger.error("Database connection failed: %s", exc, exc_info=True)  # adds traceback
```

### Example

```python
import logging

logger = logging.getLogger(__name__)

def load_agents():
    logger.debug("Starting agent load from %s", search_path)
    agents = []
    for path in search_path:
        try:
            agent = load_agent(path)
            agents.append(agent)
            logger.info("Loaded agent %s", agent.name)
        except Exception as e:
            logger.warning("Skipping agent at %s: %s", path, e)
    logger.info("Loaded %d agents", len(agents))
    return agents
```

## Configuring Log Level

### Via Environment Variable

Set `GENESIS__LOG_LEVEL` in your `.env` file or shell environment:

```bash
# .env
genesis__log_level=DEBUG
```

Or inline when running:
```bash
GENESIS__LOG_LEVEL=DEBUG uv run uvicorn ...
```

Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive). Invalid values default to `WARNING`.

### Auto-DEBUG in Dev Mode

When running with `uvicorn --reload`, the log level is automatically set to `DEBUG` regardless of config. This happens in `logging_config.py` by checking the `UVICORN_RELOAD` environment variable.

### Via Makefile

```makefile
dev-backend:
    GENESIS__LOG_LEVEL=INFO $(UV) fastapi dev $(FASTAPI_MAIN) --reload-dir $(FASTAPI_DIR)
```

Note: No `&&` needed when setting env vars inline before a command.

## Suppressing Noisy Third-Party Logs

In `setup_logging()`, third-party loggers can be set to WARNING while your app stays at DEBUG:

```python
for noisy_logger in ["uvicorn", "uvicorn.access", "fastapi", "LiteLLM", "litellm", "httpx"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)
```

This is already configured in `logging_config.py` by default.

## Log Output Format

The default format is: `[%(name)s] %(levelname)s: %(message)s`

Example output:
```
[genesis_core.agent.agent_registry] INFO: Loaded 3 agents
[uvicorn.error] INFO: Application startup complete.
```

The logger name (`%(name)s`) shows the module hierarchy, making it easy to identify where the log came from.