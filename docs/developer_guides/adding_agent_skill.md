# Adding Agent Skills

See [../agent_skill.md](../agent_skill.md) for the full architecture reference.

## Overview

A skill is a Markdown file with YAML frontmatter. Skills are reusable capability definitions that agents can reference in their manifests and access at runtime via the `read_skill` tool.

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
| `name` | `str` | Yes | Display name. Used as the skill identifier. Must match the filename stem. |
| `description` | `str` | No | Brief description shown in the system prompt skill list. |
| `version` | `str` | No | Version string. Defaults to `"1.0"`. |

### Instructions Body

The markdown body after the closing `---` is the skill instructions. This content is returned in full when the agent calls `read_skill`. Write it as if addressing the agent directly.

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

Filename becomes the skill name. Use lowercase with underscores:

```
genesis-core/src/genesis_core/skill/builtin_skills/coding_style_skill.md
```

The filename stem `coding_style_skill` is the identifier used in `allowed_skills`.

### Step 3: Write the manifest

```markdown
---
name: "Coding Style Skill"
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
allowed_skills:
  - coding_style_skill
---

You are a coding assistant specialized in Python development...
```

## How Agents Use Skills

1. **At creation time**, the agent's system prompt includes a skill list section with name and description for each allowed skill.

2. **At runtime**, the agent can call `read_skill(skill_name="coding_style_skill")` to load the full instructions into the clipboard.

3. The skill content is then available in the agent's context for the current turn and persists in the clipboard until it expires.

## Best Practices

1. **Name should match filename** — The `name` field in frontmatter should match the file stem (e.g., `coding_style_skill.md` has `name: "Coding Style Skill"` or `name: "coding_style_skill"`). Both work, but be consistent.

2. **Be specific in instructions** — Write as if instructing the agent directly. Include examples, boundaries, and step-by-step processes where relevant.

3. **Avoid em-dashes and AI clichés** — Per project conventions, use parentheses or commas instead of em-dashes. Avoid words like "delve", "leverage", "seamless", etc.

4. **Keep descriptions brief** — The description appears in the system prompt skill list. One to two sentences is enough.

5. **One skill, one focus** — Each skill should cover a single capability or domain. Split compound skills into multiple files.

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

1. **Accuracy** — Are factual claims correct? Verify against source material.
2. **Completeness** — Are key aspects covered? Check methodology, results, conclusions.
3. **Clarity** — Is the summary understandable to a non-expert?
4. **Citations** — Are sources properly referenced?

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

- [../agent_skill.md](../agent_skill.md) — full skill system architecture
- [creating_agent_manifests.md](./creating_agent_manifests.md) — defining agents that use skills