# Development Rules

This project is called `genesis-scaffolding`

## Conversational Style

- Keep answers short and concise
- No emojis in commits, issues, PR comments, or code
- No fluff or cheerful filler text
- No unicode, em-dashes, or non-ASCII characters in any text content. Plain ASCII only
- Do not use em-dashes in writing. Use comma or parentheses instead (e.g., "The process (code, test, document) must be followed" not "The process - code, test, document - must be followed")
- Technical prose only, be kind but direct (e.g., "Thanks @user" not "Thanks so much @user!")

## Overall Protocol

- Thoroughly understand the related architecture and code before answering code related questions, planning or making code change. Ensure you understand the code modules relevant to your task and the interaction between them
- Read the `README.md` and necessary docs to orient yourself. Start with `docs/architecture.md` for the system overview, `docs/architecture.md#documentation-index` for a full list of available docs, and `docs/module_reference.md` for the detailed module map. Then drill into specific docs for the area you are working on.
- Create specification of the code change and step-by-step plan to implement it and present to developer before coding. NEVER start coding before getting the plan approved
- Ask developer questions and suggest implementations to fully understand developer's requirements before writing specification and plan
- Write or modify code according to the plan
- Report to developer the progress and results after all the planned code changes have been completed and verified with tests
- AFTER developer has approved the code, add new docs and update current docs to ensure the docs accurately track the code. Refer to the [documentation.md](documentation.md) for more details regarding documentation.
- **Human developer signing off commit**. NEVER commit unless developer asks you to.

## Code Quality

- Read files in full before making wide-ranging changes, before editing files you have not already fully inspected, and when the developer asks you to investigate or audit something. Do not rely only on search snippets for broad changes.
- Check `node_modules` or `.venv` for external API type definitions instead of guessing
- **NEVER use inline imports** Always use standard top-level imports.
- Always ask before removing functionality or code that appears to be intentional
- Do not preserve backward compatibility unless the developer explicitly asks for it
- **Keep it simple**: Do not add abstraction layers and modules to "future-proof" the project. Your design need to prioritise readability and maintainability
- **Don't repeat yourself**: Adapt your proposed new code to work with the existing logic, modules, components if possible. Refactor existing logic, modules, components, into shared utilities if necessary.
- The code must pass the full suite of linting and tests before considered ready

## Commands

Use `make` whenever possible. See the `Makefile` at repo root for details about build targets.

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

# Run all checks: lint + type-check + test (both backend and frontend)
make check-all
```

If you need to run python code against python backend, always use `uv`. **Never use `python` or other python tools directly.**

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


## **CRITICAL** Git Rules for Parallel Agents **CRITICAL**

Multiple agents may work on different files in the same worktree simultaneously. You MUST follow these rules:

### Committing

- **ONLY commit files YOU changed in THIS session**
- ALWAYS include `fixes #<number>` or `closes #<number>` in the commit message when there is a related issue or PR
- NEVER use `git add -A` or `git add .` - these sweep up changes from other agents
- ALWAYS use `git add <specific-file-paths>` listing only files you modified
- Before committing, run `git status` and verify you are only staging YOUR files
- Track which files you created/modified/deleted during the session
- It is always fine to include `packages/ai/src/models.generated.ts` in a commit alongside the actual files you want to commit

### Forbidden Git Operations

These commands can destroy other agents' work:

- `git reset --hard` - destroys uncommitted changes
- `git checkout .` - destroys uncommitted changes
- `git clean -fd` - deletes untracked files
- `git stash` - stashes ALL changes including other agents' work
- `git add -A` / `git add .` - stages other agents' uncommitted work
- `git commit --no-verify` - bypasses required checks and is never allowed

### Safe Workflow

```bash
# 1. Check status first
git status

# 2. Add ONLY your specific files
git add packages/ai/src/providers/transform-messages.ts
git add packages/ai/CHANGELOG.md

# 3. Commit
git commit -m "fix(ai): description"

# 4. Push (pull --rebase if needed, but NEVER reset/checkout)
git pull --rebase && git push
```

### If Rebase Conflicts Occur

- Resolve conflicts in YOUR files only
- If conflict is in a file you didn't modify, abort and ask the developer
- NEVER force push

### developer override

If the developer instructions conflict with rules set out here, ask for confirmation that they want to override the rules. Only then execute their instructions.

## Module reference must be kept current

When you add, remove, or move a module in this codebase, update `docs/module_reference.md` to reflect the change. This file is the primary map for agents and developers to navigate the codebase — stale references break the system's ability to be understood by both human developers and AI agents.

Specifically:
- Adding a new module or package — add it to the appropriate subsection
- Removing a module — remove it from the list
- Moving a module to a different package — update location and grouping

This is not optional. Treat the module reference as part of the code change.

### Dealing with type errors

- If type error is triggered by third-party library (e.g., SQLAlchemy, Pydantic, FastAPI) and you are sure that the code works, a targeted `// @ts-ignore` or `# type: ignore` is acceptable.
- If the error is caused by mismatches against types or schemas **we define**, fix the type properly. Do not use `as any`, `as unknown`, or `type: ignore` to suppress errors from our own code.

