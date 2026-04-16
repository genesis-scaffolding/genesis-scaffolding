# Writing a New Agent

This guide explains how to create a new agent for the Genesis Scaffolding platform. Agents are defined as Markdown files with YAML frontmatter, making them easy to create, version-control, and deploy without writing Python code.

## Overview

An agent consists of:

1. **A `.md` file** in an agent search path — defines metadata and system prompt
2. **Optional tools** — capabilities the agent can call during its loop
3. **Optional agent delegation** — ability to delegate tasks to other agents

## Step 1: Create the Agent File

Place a new `.md` file in one of the configured agent search paths. The file name (without extension) becomes the agent's ID.

Agent search paths are configured in your settings. Typically:

- **Bundled agents** (read-only): `myproject-core/src/myproject_core/agents/`
- **User agents** (editable): `user_directories/{user_id}/.myproject/agents/`

## Step 2: Define the Frontmatter

The YAML frontmatter sits between `---` markers at the top of the file:

```markdown
---
name: "My Agent"
description: "A helpful agent that does X"
interactive: true
read_only: true
allowed_tools:
  - search_web
  - read_file
  - write_file
allowed_agents:
  - assistant_agent
---
```

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the agent |
| `description` | string | No | Human-readable description of what the agent does |
| `interactive` | boolean | No | If `true`, the agent can be used in chat interfaces. Default: `false` |
| `read_only` | boolean | No | If `true`, users cannot edit or delete this agent. Default: `false` |
| `allowed_tools` | list[string] | No | Tools the agent is permitted to call |
| `allowed_agents` | list[string] | No | Other agents this agent can delegate to |
| `model_name` | string | No | LLM model to use (must be configured in settings) |

## Step 3: Write the System Prompt

After the closing `---`, write the system prompt that defines the agent's behavior:

```markdown
---
name: "Research Assistant"
description: "Helps users research topics by searching the web"
---

You are a research assistant. Your goal is to help users find accurate,
up-to-date information on topics they care about.

When researching:
1. Search for multiple sources to verify information
2. Cite your sources with URLs when possible
3. Distinguish between facts and opinions
4. Be transparent about uncertainty

Keep responses concise and focused on the user's question.
```

### System Prompt Guidelines

- **Be specific** — define the agent's role, goals, and constraints
- **List steps** — for procedural tasks, enumerate the steps
- **Set boundaries** — clarify what the agent should not do
- **Output format** — specify how the agent should present results

## Tools Reference

Tools extend what the agent can do. Available tools are registered in `myproject_tools/registry.py`.

To grant an agent access to a tool, add it to `allowed_tools`:

```yaml
allowed_tools:
  - search_web
  - fetch_web_page
  - read_file
```

See [Implementing Tools](implementing-tools.md) for how to build new tools.

## Agent Delegation

For complex tasks, agents can delegate to other agents. Configure delegation:

```yaml
allowed_agents:
  - assistant_agent
  - research_agent
```

The agent can then delegate subtasks while maintaining oversight.

## Example: Research Agent

Here's a complete example of a research-focused agent:

```markdown
---
name: "Research Critic"
description: "Critiques and improves research summaries"
interactive: false
read_only: true
allowed_tools:
  - search_web
  - fetch_web_page
  - get_arxiv_paper_detail
  - search_arxiv_paper
allowed_agents:
  - research_summary
---

You are a research critic. Your role is to evaluate research summaries
for accuracy, completeness, and clarity.

Evaluation Criteria:
1. **Accuracy** — Are the factual claims correct?
2. **Completeness** — Are key aspects of the research covered?
3. **Clarity** — Is the summary understandable to a non-expert?
4. **Citations** — Are sources properly referenced?

When reviewing:
- Read the full source material before critiquing
- Provide specific, actionable feedback
- Suggest improvements with examples when possible
- Rate the summary on each criterion (1-5)
```

## Testing Your Agent

### Manual Testing

Use the CLI or Python to spawn and test your agent:

```python
from myproject_core.agent.agent_registry import AgentRegistry
from myproject_core.configs import get_config

settings = get_config()
registry = AgentRegistry(settings=settings)

# Create an instance of your agent
agent = registry.create_agent(
    "my_agent",  # Must match the filename stem
    working_directory=settings.path.working_directory,
)

# Run a test prompt
result = await agent.step(
    "Your test prompt here",
    working_directory=settings.path.working_directory,
)
print(result)
```

### Debug Output

The agent loop writes debug logs to `debug_messages.json` in the current directory. This shows the full message history including tool calls and responses — useful for tracing why an agent behaves unexpectedly.

## Best Practices

1. **Start simple** — begin with a minimal system prompt and add constraints as needed
2. **Use `read_only: true`** for bundled agents that shouldn't be modified by users
3. **Set `interactive: true`** only for agents designed for chat interfaces
4. **Limit tools** — grant only the tools the agent genuinely needs
5. **Be explicit** — clearer prompts produce more predictable behavior

## File Location Summary

| Agent Type | Location | Editable? |
|------------|----------|------------|
| Bundled agents | `myproject-core/src/myproject_core/agents/` | No (if `read_only: true`) |
| User agents | `user_directories/{id}/.myproject/agents/` | Yes |
