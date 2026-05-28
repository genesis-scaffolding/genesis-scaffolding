# Creating Agent Manifests

See [../agent_manifests.md](../agent_manifests.md) for the full architecture reference, including search paths, model resolution, and loading behavior.

## Overview

An agent is a Markdown file with YAML frontmatter. The frontmatter holds metadata, and the markdown body is the system prompt. No Python code is required.

## Structure

```markdown
---
name: "My Agent"
description: "A brief description shown in the UI"
model_name: "claude-haiku"
interactive: true
read_only: false
allowed_tools:
  - search_web
  - read_file
allowed_agents: []
is_default: false
---

You are a helpful assistant. Your goal is to ...
```

## Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Display name shown in the UI |
| `description` | `str` | `""` | Short description shown in the agent picker |
| `model_name` | `str` | `""` | Model nickname from user config. If omitted, uses the user's default model |
| `interactive` | `bool` | `false` | If `true`, the agent can be used in chat sessions. Non-interactive agents are for workflows only |
| `read_only` | `bool` | `false` | If `true`, the agent cannot be edited or deleted via the API. Set this for bundled agents |
| `allowed_tools` | `list[str]` | `[]` | Tools the agent is permitted to use |
| `allowed_agents` | `list[str]` | `[]` | Other agents this agent may delegate to |
| `is_default` | `bool` | `false` | If `true`, pre-selected for new chat sessions. Only one agent should have this |

## System prompt guidelines

After the closing `---`, write the system prompt body:

- **Be specific** — define the agent's role, goals, and constraints clearly
- **List steps** — for procedural tasks, enumerate the expected behavior
- **Set boundaries** — clarify what the agent should not do
- **Specify output format** — describe how results should be presented

## File location

Agent manifests live in the configured `agent_search_paths`. The default locations are:

| Type | Path | Editable |
|---|---|---|
| Bundled agents | `genesis-core/src/genesis_core/agent/builtin_agents/` | No (if `read_only: true`) |
| User agents | `.genesis/agents/` in user data directory | Yes |

The file stem (filename without `.md`) becomes the agent ID.

## Example: Research Agent

```markdown
---
name: "Research Critic"
description: "Critiques and improves research summaries"
interactive: false
read_only: true
allowed_tools:
  - search_web
  - fetch_web_page
  - search_arxiv_paper
allowed_agents: []
---

You are a research critic. Your role is to evaluate research summaries
for accuracy, completeness, and clarity.

Evaluation Criteria:
1. Accuracy — Are the factual claims correct?
2. Completeness — Are key aspects of the research covered?
3. Clarity — Is the summary understandable to a non-expert?
4. Citations — Are sources properly referenced?

When reviewing:
- Read the full source material before critiquing
- Provide specific, actionable feedback
- Suggest improvements with examples when possible
- Rate the summary on each criterion (1-5)
```

## Best practices

1. Start simple — begin with a minimal system prompt and add constraints as needed
2. Use `read_only: true` for bundled agents that should not be modified by users
3. Set `interactive: true` only for agents designed for chat interfaces
4. Limit `allowed_tools` to only what the agent genuinely needs
5. Be explicit — clearer prompts produce more predictable behavior
6. Use plain text in prompts — avoid em-dashes, unicode, or non-ASCII characters