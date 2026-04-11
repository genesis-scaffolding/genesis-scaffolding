# Frontend Architecture

## Overview

The frontend is a NextJS web application using the App Router. It handles server-side rendering and is deployed separately from the Python backend. Users interact with the agent and productivity system through this UI.

## Codebase Organization

```
myproject-frontend/
├── proxy.ts                # Edge Runtime middleware (intercepts all requests)
├── app/                    # Next.js App Router pages and layouts
│   ├── actions/            # Server Actions (data mutations, API calls)
│   ├── api/[...proxy]/     # API proxy route (forwards to FastAPI)
│   ├── dashboard/          # Dashboard pages (projects, tasks, journals, agents, etc.)
│   ├── login/              # Login page
│   └── register/           # Registration page
├── components/
│   ├── auth/               # Auth components (login form, logout button)
│   ├── chat/               # Chat UI components
│   ├── dashboard/          # Dashboard-specific components
│   │   ├── shared/data-table/   # TanStack Table engine and shared table components
│   │   ├── tasks/          # Task-specific components
│   │   ├── projects/       # Project-specific components
│   │   ├── journals/       # Journal-specific components
│   │   ├── sandbox/        # Sandbox file viewer components (FileViewer, Breadcrumb)
│   │   └── ...             # Other domain-specific components
│   └── ui/                 # Shadcn UI component library
├── lib/                    # Client-side utilities
│   ├── api-client.ts       # Typed API client for server-side fetch
│   ├── auth.ts             # Auth utilities (including shared token refresh)
│   ├── session.ts          # Cookie management (Route Handler only)
│   ├── date-utils.ts       # Date formatting helpers
│   └── ...
├── types/                  # TypeScript interface definitions
│   ├── api.ts              # General API types
│   ├── auth.ts             # Auth types
│   ├── chat.ts             # Chat message types
│   ├── productivity.ts     # Task, project, journal types
│   └── ...
└── hooks/                  # React hooks
```

## App Router

The frontend uses Next.js App Router (`app/` directory). Routes are defined by the file system structure under `app/`. Each route can have:

- `page.tsx` — The page component (server or client)
- `layout.tsx` — A shared layout wrapping child pages
- `loading.tsx` — A loading state for the route

### Dashboard Routes

The main application lives under `app/dashboard/`:

| Path | Description |
|---|---|
| `app/dashboard/page.tsx` | Dashboard home |
| `app/dashboard/tasks/` | Task list and management |
| `app/dashboard/projects/` | Project management |
| `app/dashboard/journals/` | Journal entries |
| `app/dashboard/agents/` | Agent configuration |
| `app/dashboard/chats/` | Chat history |
| `app/dashboard/jobs/` | Workflow job monitoring |
| `app/dashboard/workflows/` | Workflow management |
| `app/dashboard/schedules/` | Schedule management |
| `app/dashboard/memory/` | Agent memory viewer |
| `app/dashboard/files/` | File sandbox browser with directory navigation |
| `app/dashboard/files/[id]/` | In-page file viewer with content preview (markdown, code, images) |
| `app/dashboard/settings/` | User settings |
| `app/dashboard/calendar/` | Calendar view |

## Server Actions

Form submissions and data mutations run server-side via NextJS Server Actions in `app/actions/`. Server Actions are async functions that execute on the server and can return data to client components.

Example server action pattern:

```typescript
// app/actions/tasks.ts
'use server'
import { apiFetch } from "@/lib/api-client";
import { revalidatePath } from "next/cache";

export async function getTasksAction() {
  const res = await apiFetch(`/productivity/tasks/`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTaskAction(data: TaskCreateInput) {
  const res = await apiFetch(`/productivity/tasks/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/tasks');
  return res.json();
}
```

## API Proxy

All browser requests to FastAPI are routed through `app/api/[...proxy]/route.ts`. This proxy forwards requests to the FastAPI backend, ensuring credentials and API keys are never exposed to the client browser.

The `apiFetch` utility in `lib/api-client.ts` is the standard way to make API calls — it handles the proxy path and authentication headers.

## Edge Runtime Middleware

`proxy.ts` at the project root is a Next.js middleware function that runs in the **Edge Runtime** — it intercepts every request before it reaches any page or API route. This is distinct from Route Handlers (`app/api/`) which run in Node.js.

### Execution environments

| Environment | Where it runs | Can use `next/headers` | Can use Node.js modules |
|---|---|---|---|
| Edge Runtime (middleware) | CDN edge nodes | ✗ | ✗ |
| Route Handlers / Server Components | Node.js server | ✓ | ✓ |

### What proxy.ts does

- Intercepts all requests matching the matcher pattern
- Decodes the JWT access token to check expiry
- If access token is expired but refresh token exists, calls `POST /auth/refresh` and sets the new access token cookie directly on the response
- Redirects unauthenticated users to `/login`
- Clears auth cookies when entering auth paths (`/login`, `/register`)

### Cookie handling in Edge vs Route Handler contexts

`lib/session.ts` uses `cookies()` from `next/headers`, which only works in Route Handlers and Server Components — not in Edge Runtime. The `proxy.ts` middleware must set cookies using the standard Web API on `NextResponse`:

```typescript
// In Edge Runtime (proxy.ts):
const response = NextResponse.next();
response.cookies.set('access_token', newToken, { httpOnly: true, ... });
return response;

// NOT:
// cookies().set(...)  — next/headers, not available in Edge Runtime
```

The `refreshAccessToken()` function in `lib/auth.ts` is shared between both contexts — it only performs the HTTP call and returns tokens, without persistence.

## Dashboard Layout

The dashboard uses a shared layout with a collapsible sidebar (`app/dashboard/layout.tsx`). The layout structure:

```
<SidebarProvider>
  <Sidebar>              # Navigation sidebar with grouped menu items
  <div>
    <header>            # Top bar with sidebar trigger and dynamic header
    <main>              # Page content area
  </div>
</SidebarProvider>
```

Navigation is organized into groups: **Productivity**, **Interaction**, **Automation**, and **Knowledge**.

## Page Layout System

Dashboard pages use two helper components to ensure consistent layout and prevent scroll issues:

- **`PageContainer`** (`components/dashboard/page-container.tsx`) — Constrains width and manages scroll behavior per variant
- **`PageBody`** (`components/dashboard/page-container.tsx`) — Provides standard padding and spacing

See [frontend-pages.md](frontend-pages.md) and [frontend-components.md](frontend-components.md) for detailed usage.

## Data Tables

TanStack Table is used for listing and filtering productivity entities. The implementation spans two directories:

- **`components/dashboard/shared/data-table/`** — Shared table engine (`DataTable`, `DataTableColumnHeader`, pagination controls)
- **`components/dashboard/[entity]/`** — Entity-specific column definitions and table orchestrators

See [frontend-tables.md](frontend-tables.md) for detailed usage patterns.

## Chat UI

The chat interface communicates with the backend via Server-Sent Events (SSE) at `/api/chats/{id}/stream`. For full streaming architecture details, see [myproject-server/sse-streaming.md](../myproject-server/sse-streaming.md).

## Sandbox File Browser

The sandbox file browser (`app/dashboard/files/`) provides a filesystem-like interface for users to upload, browse, and preview files in their sandboxed working directory.

### Types

```typescript
// types/sandbox.ts
interface SandboxFile {
  relative_path: string;  // Primary identifier (base64url-encoded for URLs)
  name: string;
  is_dir: boolean;
  size: number | null;
  mime_type: string | null;
  mtime: number | null;
  created_at: string | null;
}

// File ID encoding: base64url encoding of relative_path
export function encodeFileId(relativePath: string): string;
export function decodeFileId(encoded: string): string;
```

### Server Actions

```typescript
// app/actions/sandbox.ts
export async function getFilesAction(folder?: string): Promise<SandboxFile[]>
export async function getFoldersAction(parentFolder?: string): Promise<string[]>
export async function getFileAction(relativePath: string): Promise<{ file: SandboxFile; content?: string }>
export async function uploadFileAction(formData: FormData): Promise<SandboxFile>
export async function deleteFileAction(relativePath: string): Promise<void>
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `SandboxFileExplorer` | `components/dashboard/sandbox-file-explorer.tsx` | Main container; manages search, folders, and files in a unified table |
| `SandboxTable` | `components/dashboard/sandbox/sandbox-table.tsx` | TanStack Table wrapper for file listing |
| `FileViewer` | `components/dashboard/sandbox/file-viewer.tsx` | File content preview (text, markdown, images, PDF download) |
| `Breadcrumb` | `components/dashboard/sandbox/breadcrumb.tsx` | Navigation breadcrumb |
| `buildSandboxBreadcrumbs` | `components/dashboard/sandbox/breadcrumbs.ts` | Utility to build breadcrumb items from a relative path |

### URL Structure

- `/dashboard/files` — Browse sandbox root or a specific folder
- `/dashboard/files?folder=docs/papers` — Browse specific folder
- `/dashboard/files/{encoded_path}` — View specific file (relative_path is base64url-encoded)

## Tech Stack

- **Framework**: Next.js (App Router)
- **UI Components**: Shadcn UI
- **Icons**: Lucide-react
- **Styling**: Tailwind CSS / PostCSS
- **Tables**: TanStack Table
- **Forms**: React Hook Form + Zod

## Related Modules

- `myproject_frontend/app/` — App Router pages and layouts
- `myproject_frontend/app/actions/` — Server Actions
- `myproject_frontend/app/api/[...proxy]/` — API proxy route
- `myproject_frontend/components/dashboard/` — Dashboard components including page-container
- `myproject_frontend/components/dashboard/shared/data-table/` — TanStack Table engine
- `myproject_frontend/lib/api-client.ts` — API client utility
