# Data Flow: Browser, Next.js, and FastAPI

The browser never talks to FastAPI directly. Every request goes to Next.js first, which either handles it directly or forwards it to FastAPI.

## Two Communication Paths

### Server Actions (auth only)

Used for login, logout, and registration. These operations must call FastAPI directly because they need to receive and set session cookies on the browser.

```
Browser → Server Action → FastAPI → Set-Cookie on response → Browser
```

Flow:
1. User submits form
2. Server Action calls `authenticateUser()` in `lib/auth.ts`
3. `authenticateUser()` POSTs credentials to `http://localhost:8000/auth/login`
4. On success, FastAPI returns access_token and refresh_token
5. Server Action calls `createSession()` in `lib/session.ts` to set httpOnly cookies
6. Browser stores the cookies automatically

Key files:
- `app/actions/auth.ts` — loginAction, logoutAction, registerAction
- `lib/auth.ts` — authenticateUser, refreshAccessToken
- `lib/session.ts` — createSession, getAccessToken, deleteSession

### API Proxy (all other calls)

Used for chat, workflows, tasks, projects, and everything else.

```
Browser → GET /api/[path] → Next.js route handler → apiFetch → FastAPI
```

Flow:
1. Browser calls `/api/agents/`, `/api/chats/`, etc.
2. Next.js route handler `app/api/[...proxy]/route.ts` receives the request
3. Route handler calls `apiFetch()` from `lib/api-client.ts`
4. `apiFetch()` reads `access_token` from cookies
5. `apiFetch()` sets `Authorization: Bearer <token>` header
6. `apiFetch()` POSTs to FastAPI and returns the response

Key files:
- `app/api/[...proxy]/route.ts` — GET and POST route handlers
- `lib/api-client.ts` — apiFetch, apiGet, apiPost, apiPut, apiDelete

## How apiFetch Works

```typescript
// lib/api-client.ts (simplified)
export async function apiFetch(endpoint, options = {}) {
  const accessToken = await getAccessToken();        // Read cookie
  headers.set('Authorization', `Bearer ${accessToken}`);  // Inject token

  let response = await fetch(`${FASTAPI_URL}${endpoint}`, { headers });

  // If FastAPI returns 401, try token refresh
  if (response.status === 401) {
    const refreshed = await refreshAccessToken(refreshToken);
    if (refreshed) {
      await createSession(refreshed.access_token, refreshed.refresh_token, ...);
      headers.set('Authorization', `Bearer ${refreshed.access_token}`);
      response = await fetch(`${FASTAPI_URL}${endpoint}`, { headers });  // Retry
    }
  }

  return response;
}
```

## Where Token Injection Happens

Token injection is the step of reading the access token from a cookie and attaching it as the `Authorization: Bearer` header on outgoing requests. It happens in two places:

1. **Edge Middleware (`proxy.ts`)** — Intercepts all requests before they reach any page or route. Checks if access token is expired. If so, calls `POST /auth/refresh` and sets a new cookie on the response before forwarding.

2. **apiFetch (`lib/api-client.ts`)** — Attaches the token to every API call made through the proxy route. Also handles 401 with automatic refresh.

## Server Actions Pattern

Server Actions live in `app/actions/` and are marked with `'use server'`. They run on the Next.js server, can access cookies and headers, and return data to client components.

Example pattern from `app/actions/chat.ts`:

```typescript
'use server'

import { apiFetch } from "@/lib/api-client";

export async function getAgentsAction(): Promise<Agent[]> {
  const res = await apiFetch(`/agents/`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function createAgentAction(data: AgentCreate): Promise<Agent> {
  const res = await apiFetch(`/agents/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/agents');  // Refresh the page data
  return res.json();
}
```

## Request Flow Summary

```mermaid
sequenceDiagram
    participant Browser
    participant NextJS as Next.js
    participant Middleware as Edge Middleware
    participant apiFetch as apiFetch
    participant FastAPI as FastAPI

    rect rgb(245, 248, 255)
        Note over Browser,FastAPI: 1. Login flow (Server Action)
        Browser->>NextJS: POST /login (form data)
        NextJS->>FastAPI: POST /auth/login (credentials)
        FastAPI-->>NextJS: TokenResponse (access_token, refresh_token)
        NextJS->>Browser: Set-Cookie (httpOnly)
        Browser->>NextJS: GET /dashboard
    end

    rect rgb(240, 248, 245)
        Note over Browser,FastAPI: 2. Page load (Edge Middleware)
        Browser->>Middleware: GET /dashboard<br/>Cookie: access_token
        Middleware->>Middleware: decode JWT, check exp
        alt access token valid
            Middleware->>NextJS: NextResponse.next()
        else access token expired
            Middleware->>FastAPI: POST /auth/refresh
            FastAPI-->>Middleware: new access_token
            Middleware->>Browser: Set-Cookie (new access_token)
        end
        NextJS->>FastAPI: GET /users/me (server component)
        FastAPI-->>NextJS: User JSON
        NextJS-->>Browser: Page (HTML + React)
    end

    rect rgb(255, 245, 248)
        Note over Browser,FastAPI: 3. API call via proxy (apiFetch)
        Browser->>NextJS: fetch /api/agents/<br/>Cookie: access_token
        NextJS->>apiFetch: call /agents/
        apiFetch->>apiFetch: read access_token cookie<br/>set Authorization: Bearer <token>
        apiFetch->>FastAPI: GET /agents/<br/>Authorization: Bearer <token>
        FastAPI-->>apiFetch: JSON response
        apiFetch-->>NextJS: JSON
        NextJS-->>Browser: JSON response
    end
```

The three flows cover the complete lifecycle:
1. **Login** — Server Action calls FastAPI directly, receives tokens, sets httpOnly cookies
2. **Page load** — Edge Middleware checks token expiry and refreshes if needed before the page renders
3. **API call** — Browser fetches the proxy route, apiFetch injects the token, FastAPI returns data

## Authentication Reference

For complete auth details — JWT structure, token refresh flow, logout, and known limitations — see [authentication.md](./authentication.md).

## Optimistic Mutation Flow

When a user mutation should feel instant (status change, task creation), the page wraps the relevant components in an optimistic state provider (see [frontend_components/task-list-provider.md](./frontend_components/task-list-provider.md) for the canonical example). The flow is:

1. **User action** — the user clicks a status badge, submits a new task, etc.
2. **Synchronous UI feedback** — close the popover, clear the input, show the spinner. These run outside any transition so the user sees the change immediately.
3. **`startTransition` with `addOptimistic`** — the component dispatches an optimistic action (e.g. `{ type: "status", taskId, status }` or `{ type: "create", task }`). React updates the visible state in the same frame from the optimistic layer.
4. **Server action in the background** — the same transition calls the server action (e.g. `updateTaskAction`, `createTaskAction`). The action PATCHes/POSTs to FastAPI through the proxy.
5. **`router.refresh()` in the same transition** — triggers a server-side re-render of the current page. The new RSC payload arrives with the authoritative `tasks` prop.
6. **Reconciliation** — `useOptimistic` reconciles: the new `tasks` prop becomes the base state, the optimistic overlay is dropped, and the default sort/filter rules apply.

If the server action throws, the transition completes without a new `tasks` prop arriving, and React reverts the optimistic state to the previous value. The user sees the row snap back to its original state.

```
User clicks badge
    │
    ▼
Synchronous UI feedback (close popover, clear input)
    │
    ▼
startTransition(() => {
    addOptimistic({ type: "status", taskId, status })  ← React re-renders from optimistic layer
    await updateTaskAction(...)                        ← server round-trip
    router.refresh()                                   ← trigger RSC re-render
})
    │
    ▼
New RSC payload arrives with authoritative tasks
    │
    ▼
useOptimistic reconciles: optimistic overlay dropped, base state updated
```

Key properties of this pattern:

- **The optimistic layer is the single source of truth inside the transition.** Components that render the row data read from the optimistic context, not from any prop they were passed, so a status flip or a new row is visible in the same frame as the click.
- **The transition boundary wraps only the dispatch + server call + revalidation, not the synchronous UI feedback.** Wrapping the input clear inside the transition would delay the feedback until the transition starts.
- **The provider's default context is a no-op.** Components rendered outside any provider (e.g. the floating `QuickAddTask` in the dashboard layout) see a no-op dispatch and fall back to `router.refresh()` for reconciliation, so the same component works in both wrapped and unwrapped modes.

See [frontend_components/task-list-provider.md](./frontend_components/task-list-provider.md) and [frontend_components/task-table.md](./frontend_components/task-table.md) for the concrete wiring on the task list pages.