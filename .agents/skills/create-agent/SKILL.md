---
name: create-agent
description: >
  Create a new agent manifest in YAML. Use when the user asks to "create an agent",
  "add an agent", "create agent", "build an agent", or "make a new agent". This skill
  handles the full process from understanding requirements to producing a working
  agent YAML manifest.
---

# Create Agent

Create a new agent manifest in Markdown with YAML frontmatter.

## Workflow

### Step 1: Read the Guide

Before doing anything else, load `docs/agent_manifests.md` to understand the manifest format and field reference.

### Step 2: Clarify Requirements

Engage with the developer to understand what they want to build. Ask about:

- **Name**: What is the agent's human-readable name? (required, shown in UI)
- **Description**: What does this agent do? (required, short, shown in UI agent picker)
- **System prompt**: What instructions should guide the agent's behavior? (required)
- **Tools**: Which tools should this agent be permitted to use? (list of tool names, default: none)
- **Model**: Which model should this agent use? (optional, omit for user's default)
- **Interactive**: Should this agent be selectable for chat sessions? (bool, default: false)
- **Scope**: Is this for a specific user or shared across the server?
  - If user ID provided: write to `user_directories/<user_id>/.genesis/agents/`
  - If shared: write to `genesis-core/src/genesis_core/agent/builtin_agents/`

### Step 3: Create Preliminary Design

Based on the requirements and your understanding of the docs, draft the manifest:

- Filename (slugified from name)
- Frontmatter fields (name, description, model_name, interactive, allowed_tools, allowed_agents, is_default)
- System prompt body

Present this to the developer for review.

### Step 4: Iterate Until Approved

Refine the design based on developer feedback. Repeat until the developer approves.

### Step 5: Write the Manifest

Only after approval, write the markdown file:

- Slugify the name to generate the filename (e.g., "My Agent" becomes "my_agent.md")
- Handle filename collisions by appending a UUID suffix
- If user ID was provided, write to `user_directories/<user_id>/.genesis/agents/`
- Otherwise, write to `genesis-core/src/genesis_core/agent/builtin_agents/`

After writing, confirm the location and suggest reloading the agent harness for the new agent to be detected.

## Reference

For the full manifest format and field reference, read `docs/agent_manifests.md`.