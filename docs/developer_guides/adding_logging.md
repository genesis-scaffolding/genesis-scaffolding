# Adding Logging to Backend Code

See [../logging.md](../logging.md) for the logging architecture and configuration details.

## Quick reference

### 1. Get a logger

```python
import logging

logger = logging.getLogger(__name__)
```

Using `__name__` gives automatic hierarchy. For example, in `genesis_server/routers/chat.py`, the logger name is `genesis_server.routers.chat`.

### 2. Use the right log level

| Level | When to use |
|---|---|
| DEBUG | Dev details, loop iterations, variable states |
| INFO | Significant milestones, successful operations |
| WARNING | Recoverable issues, degraded behavior |
| ERROR | Operation failed but the app continues |

### 3. Use %-formatting

Always use `%-formatting` instead of f-strings. Arguments are only formatted when the log level is enabled.

```python
# Correct — lazy evaluation
logger.debug("Loading agent %s from %s", agent_id, path)
logger.info("Agent %s loaded successfully", agent_id)

# Wrong — always formats even when disabled
logger.debug(f"Loading agent {agent_id} from {path}")
```

### 4. Include context for errors

```python
logger.error("Failed to load agent %s: %s", agent_id, exc)
logger.error("Database connection failed: %s", exc, exc_info=True)  # adds traceback
```

## Example

```python
import logging

logger = logging.getLogger(__name__)

def load_agents(search_path: list[Path]) -> list[Agent]:
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