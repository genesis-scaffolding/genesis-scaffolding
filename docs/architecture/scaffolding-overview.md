# Genesis Scaffolding — Architecture Overview

Genesis Scaffolding is a general-purpose, capability-stacked application scaffolding for building production-ready LLM-powered applications. It provides a modular foundation where developers pick and choose which capabilities to use.

For the project's purpose statement, see `docs/project_goals.md`.

---

## High-Level Structure

The codebase splits into **frontends** and a **platform**:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontends (Optional)                        │
│   NextJS Web App · CLI · TUI (stub)                              │
├──────────────────────────────────────────────────────────────────┤
│                     Platform (FastAPI + Python)                   │
│   Server handles HTTP, auth, SSE streaming, scheduling            │
│   Python packages provide shared logic for agents, tools, etc.    │
└──────────────────────────────────────────────────────────────────┘
```

- **NextJS web frontend** — Dashboard, productivity UI, agent chat interface
- **CLI (Typer)** — Command-line entry point for local/single-user mode
- **TUI (Textual)** — Terminal user interface (early-stage stub)
- **Platform** — The server and Python packages everything else builds on

The platform splits into:
- **Python packages** — Shared business logic (agent loop, tools, workflows, memory)
- **FastAPI server** — REST API, auth, SSE broadcasting, job scheduling

---

## Deployed Architecture

When the application is deployed, three processes run independently:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User's Browser                               │
│  (React SPA — receives HTML, hydrates, makes API calls to Next.js)   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTP/HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Next.js Server                               │
│  (Process 1 — handles SSR, serves React, proxies API to FastAPI)     │
│  - Receives browser requests                                        │
│  - Server Actions for mutations (login, forms)                       │
│  - API proxy route /api/[...proxy] for fetch-based API calls          │
│  - Manages session cookies                                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTP (internal)
                                  │ or same-process call
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                               │
│  (Process 2 — REST API, auth, SSE, background jobs)                  │
│  - All /auth/*, /users/*, /chat/*, etc. endpoints                   │
│  - JWT validation, per-user database isolation                       │
│  - No knowledge of React or Next.js                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Process Responsibilities

| Process | Role | Listens on |
|---|---|---|
| **Browser (React)** | UI, form submission, session cookie storage | N/A (client) |
| **Next.js** | SSR, auth via server actions, API proxy | Port 3000 (default) |
| **FastAPI** | Business logic, auth tokens, data | Port 8000 (default) |

### Request Flow: Browser to FastAPI

The frontend makes API calls in two ways:

1. **Server Actions** (for auth: login, logout, register)
   - `lib/auth.ts` calls `/auth/login` via `fetch()` with an absolute URL (`http://localhost:8000/auth/login`)
   - This is a direct browser → FastAPI call, but the response sets cookies on the Next.js domain
   - Used for operations that need to set session cookies

2. **API Proxy** (for all other API calls)
   - `lib/api-client.ts` sends requests through `/api/[...proxy]` (Next.js route)
   - Next.js forwards to FastAPI, returning the response to the browser
   - The proxy reads `access_token` from cookies and adds `Authorization: Bearer` header
   - Used for chat, workflows, productivity, etc.

### Why Two Paths?

Server actions for auth must call FastAPI directly because they need to receive and store session cookies in the browser. The proxy cannot forward cookies from the browser to FastAPI (httponly, secure cookies are not accessible via JavaScript). For all other API calls, the proxy pattern keeps the FastAPI URL hidden from the browser and provides a consistent same-origin request path.

---

## Sub-Repositories

Each sub-repo is documented in its own directory. Read the sub-repo directory for an introduction to that part of the system.

### `myproject-core/`

The shared Python library. No other package depends on the server, CLI, or tools. Contains the core capabilities:

- **Agent subsystem** (`agent/`) — Loop execution, clipboard, prompts, memory
- **LLM client** — Provider-agnostic interface (LiteLLM + Anthropic SDK)
- **Configuration** — Three-layer config loading, environment variables, user isolation
- **Productivity** — Tasks, Projects, Journals: models and service layer
- **Workflow** — Blackboard-pattern pipeline orchestration
- **Workspace** — Sandboxed filesystem for workflow jobs

**Start here for:** building agentic features, understanding how the agent works, configuring the system.

### `myproject-server/`

FastAPI REST API. Depends on `myproject-core` and `myproject-tools`.

- **Routers** — All REST endpoints organized by domain
- **Auth** — JWT-based authentication
- **Scheduler** — APScheduler integration for cron jobs
- **SSE Streaming** — ChatManager and ActiveRun for real-time agent output

**Start here for:** adding new API endpoints, understanding auth, understanding how background jobs work.

### `myproject-tools/`

Tool implementations that extend the agent's capabilities. Depends on `myproject-core`.

- **BaseTool ABC** — The contract all tools implement
- **Tool categories** — File operations, web, productivity, memory, utilities

**Start here for:** building new tools for the agent to call.

### `myproject-frontend/`

NextJS web frontend. Separate repository structure from the Python packages.

- **Frontend architecture** — App Router, server actions, API proxy pattern
- **Auth** — Frontend authentication handling
- **Chat** — Real-time chat UI with SSE

**Start here for:** building frontend features, understanding how the frontend communicates with the backend.

### `myproject-cli/`

Typer-based CLI for single-user mode. Bypasses the FastAPI server entirely — talks directly to Python packages.

### `myproject-tui/`

Textual-based terminal UI. Currently a stub.

---

## Example Applications

The scaffolding is deliberately flexible:

| Application | Capabilities Used |
|---|---|
| **Personal AI Assistant** | All — agent, workflows, scheduling, productivity, memory, multi-user server |
| **Pure CRUD Dashboard** | FastAPI + NextJS frontend only — no agent, workflows, or tools |
| **Agent-Enabled Specialized App** | Agent + tools + workflows; add domain-specific agents and custom tools |
| **CLI-Only App** | Forego the frontend; extend the CLI with Typer commands |
| **Custom Frontend** | Redesign the frontend look and feel; backend API remains unchanged |

---

## Design Principles

- **Clarity over Abstraction** — Thin architecture close to the logic. No unnecessary layers obscuring implementation.
- **Well-defined Dependencies** — No circular dependencies. Each package has a narrowly defined purpose.
- **Canonical Tooling** — Standard libraries: FastAPI, Pydantic, SQLModel, uv, LiteLLM, Anthropic SDK, NextJS, TanStack Table.
- **Pick Your Complexity** — Start with what you need. Add capabilities as your application grows.
