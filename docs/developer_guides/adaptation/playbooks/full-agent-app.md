# Playbook: Full Agent App

**Use when:** The app needs everything — base web app, productivity, workflows, and agents. This is the current Genesis Scaffolding demo application.

This playbook keeps all extensions. Apply [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) first, then apply this one.

---

## What to Keep

Everything. This playbook is the starting point — keep the full scaffold.

### What to Remove
Only remove subsystems the user explicitly says they don't want. Ask first.

---

## Adding Domain Logic

### New Backend Entity
Add to the existing structure following [Adding Entities](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-server%2Fadding-entities.md&type=code).

### New Tool
Follow the [Implementing Tools](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-agent%2Fimplementing-tools.md&type=code) guide.

Register in `genesis-tools/registry.py`.

### New Agent
Follow the [Writing Agents](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fextending-the-agent%2Fwriting-agents.md&type=code) guide.

Add a new `.md` file to `genesis-core/src/genesis_core/agents/`.

### New Workflow Task Type
Create in `genesis-core/src/genesis_core/workflow_tasks/`.

Follow existing task patterns and register in `registry.py`.

---

## What NOT to Do

- Do NOT create new packages for domain logic — add to the appropriate existing package
- Do NOT create new registries or interfaces without a clear need
- Do NOT import from packages you just created into the server — add directly
- All other restrictions from [core-web-app.md](https://github.com/search?q=repo%3Aanthropics%2Fclaude-code%20path%3Adocs%2Fdeveloper_guides%2Fadaptation%2Fcore-web-app.md&type=code) apply

---

## Smoke Test

After adaptation:
```bash
uv run pyright .
cd genesis-frontend && pnpm build
```
