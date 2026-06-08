# Adding Agent Skills

See [../agent_skill.md](../agent_skill.md) for the full architecture reference.

## Overview

A skill is a Markdown file with YAML frontmatter. Skills are reusable capability definitions that agents can reference in their manifests and access at runtime via the `activate_skill` tool.

## When to Create a Skill

Create a skill when:

- Multiple agents need the same specialized behavior (e.g., writing guidelines, coding standards, review processes)
- The behavior is complex enough to warrant a detailed instruction document
- You want to separate the skill definition from the agent's system prompt

If only one agent needs a behavior, consider embedding it directly in that agent's system prompt instead.

## Skill Manifest Format

Skills live in Markdown files with YAML frontmatter:

```markdown
---
name: "My Skill"
description: "Brief description shown to the LLM"
version: "1.0"
---

# My Skill

Detailed instructions for the skill...
```

### Frontmatter Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Display name and the skill identifier (used in `allowed_skills` and in `activate_skill` calls). The filename stem has no required relationship to this value. Surrounding whitespace is stripped at load and lookup time. |
| `description` | `str` | No | Brief description shown in the system prompt skill list. Write this as a trigger condition - state when the agent should call `activate_skill` to load this skill. |
| `version` | `str` | No | Version string. Defaults to `"1.0"`. |

### Instructions Body

The markdown body after the closing `---` is the skill instructions. This content is returned in full when the agent calls `activate_skill`. Write it as if addressing the agent directly. Include step-by-step processes, examples, and clear boundaries.

## Where to Place Skills

### Builtin Skills

For skills that ship with the package:

```
genesis-core/src/genesis_core/skill/builtin_skills/
```

These are read-only. Place only skills that are universally applicable here.

### User Skills

For user-specific skills:

```
.genesis/skills/
```

This directory is created automatically in the user's internal state directory. User skills can be edited and deleted.

## Creating a New Skill

### Step 1: Choose a location

- For universal skills used by many agents, create the manifest in `builtin_skills/`
- For user-specific skills, create the manifest in `.genesis/skills/`

### Step 2: Create the manifest file

Choose a descriptive filename for filesystem organisation. The filename itself is not used as the identifier — the `name` field in the frontmatter is. A common convention is to use lowercase with underscores and have the filename stem match `name` for readability, but they are decoupled:

```
genesis-core/src/genesis_core/skill/builtin_skills/coding_style_skill.md
```

In `allowed_skills` (and in `activate_skill` calls), refer to the skill by its frontmatter `name`, not by the filename.

### Step 3: Write the manifest

```markdown
---
name: "coding_style_skill"
description: "Guidelines for writing maintainable Python code"
version: "1.0"
---

# Coding Style Skill

You are a coding style specialist. When writing or reviewing Python code, follow these guidelines:

## Naming Conventions

- Use `snake_case` for variables and functions
- Use `PascalCase` for classes
- Use `SCREAMING_SNAKE_CASE` for constants

## Code Structure

- Keep functions short (under 40 lines)
- Each function should do one thing
- Use type hints where beneficial

## Documentation

- Docstrings for all public functions and classes
- Inline comments for non-obvious logic
- Keep comments focused on why, not what
```

### Step 4: Reference the skill in an agent manifest

In the agent's `allowed_skills` list:

```yaml
---
name: "Code Assistant"
description: "Helps with coding tasks"
allowed_tools:
  - read_file
  - write_file
  - edit_file
  - activate_skill
allowed_skills:
  - coding_style_skill
---

You are a coding assistant specialized in Python development...
```

## Adding the `activate_skill` Tool

**The `activate_skill` tool must be present in `allowed_tools` for the skill system to function.** Without it, the skill section is not injected into the system prompt and the agent cannot load skill instructions at runtime.

> This is a temporary friction. In a future version, `activate_skill` will be injected automatically when `allowed_skills` is populated, removing the need to add it manually.

If `activate_skill` is present but a skill referenced in `allowed_skills` cannot be found, the agent will still start but the skill will not appear in the session skill list.

## Auto-injection of Missing Builtin Skills

When `activate_skill` is in the tool list, the system automatically adds any builtin skill that maps to the agent's tools but is missing from `allowed_skills`. A warning is logged:

```
Agent 'Max' has tools ['web_search', 'remember_this'] but is missing the
corresponding skill(s) ['web', 'memory']. Automatically
injected for this session. Add these skills to the agent manifest's
allowed_skills list.
```

This prevents the agent from having powerful tools without guidance. To fix it permanently, add the missing skill names to the agent manifest's `allowed_skills` list.

The tool-to-skill mapping is documented in [../agent_skill.md](../agent_skill.md#auto-injection-of-missing-builtin-skills).

## How Agents Use Skills

1. **At creation time**, the system prompt includes a skill instruction fragment that tells the agent when to call `activate_skill`, lists available builtin skills, and lists the skills active for this session.

2. **At runtime**, the agent calls `activate_skill(skill_name="coding_style_skill")` to load the full instructions into the clipboard.

3. The skill content is then available in the agent's context for the current turn and persists in the clipboard until it expires.

## Best Practices

1. **Choose a stable `name` and reference skills by it** - The frontmatter `name` is the identifier the registry keys on and the only thing that matters for `allowed_skills` and `activate_skill` calls. The filename is free to choose; pick something readable and keep it stable. A common convention is to use lowercase_with_underscores and to mirror `name` in the filename stem for grep-ability, but it is not enforced.

2. **Write the description as a trigger condition** - State explicitly when the agent should load this skill. For example: "Use this skill when user asks to write or review code."

3. **Be specific in instructions** - Write as if instructing the agent directly. Include examples, boundaries, and step-by-step processes where relevant.

4. **Avoid em-dashes and AI cliches** - Per project conventions, use parentheses or commas instead of em-dashes. Avoid words like "delve", "leverage", "seamless", etc.

5. **Keep descriptions brief** - The description appears in the system prompt skill list. One to two sentences is enough.

6. **One skill, one focus** - Each skill should cover a single capability or domain. Split compound skills into multiple files.

## Example: Research Review Skill

```markdown
---
name: "research_review"
description: "Guidelines for reviewing and critiquing research summaries"
version: "1.0"
---

# Research Review Skill

You are a research critic. Your role is to evaluate research summaries for accuracy, completeness, and clarity.

## Evaluation Criteria

1. **Accuracy** - Are factual claims correct? Verify against source material.
2. **Completeness** - Are key aspects covered? Check methodology, results, conclusions.
3. **Clarity** - Is the summary understandable to a non-expert?
4. **Citations** - Are sources properly referenced?

## Review Process

1. Read the full source material before providing feedback.
2. Identify the main claims and supporting evidence.
3. Note any gaps, inconsistencies, or overstatements.
4. Provide specific, actionable feedback with examples.
5. Rate the summary on each criterion (1-5).

## Output Format

When reviewing, structure your response as:

- **Strengths**: What is done well
- **Areas for improvement**: Specific suggestions
- **Overall rating**: 1-5 with justification
```

## See also

- [../agent_skill.md](../agent_skill.md) - full skill system architecture
- [creating_agent_manifests.md](./creating_agent_manifests.md) - defining agents that use skills