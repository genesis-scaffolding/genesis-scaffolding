# Frontend Authentication

## Overview

The frontend communicates with the FastAPI backend using JWT-based authentication. The frontend never stores passwords — it exchanges credentials for tokens and uses those tokens on every subsequent request.

## Auth Flow

### Login

1. User submits credentials via the login form (a server action calls `lib/auth.ts`)
2. `POST /auth/login` is made to FastAPI (via direct fetch in the server action, not the proxy)
3. Server validates credentials and returns an access token (15-min JWT) and a refresh token (7-day opaque token)
4. Frontend calls `lib/session.ts` `createSession()` to store both tokens as httpOnly cookies
5. On success, the form redirects to `/dashboard`

### Authenticated Requests

The dashboard layout (`app/dashboard/layout.tsx`) calls `getCurrentUser()` on every page load. This reads the access token from cookies and validates it against FastAPI via the proxy route.

For API calls from server actions, `lib/api-client.ts` reads the access token from cookies and forwards it as `Authorization: Bearer <token>` to FastAPI through the proxy.

For API calls from client components, the same `apiFetch` path is used — the proxy reads the cookie and adds the Authorization header.

### Token Refresh

Token refresh happens in two places, for different request contexts:

**1. Route Handlers (API calls)** — `lib/api-client.ts`

When an API call returns HTTP 401, `apiFetch` automatically sends the refresh token to `POST /auth/refresh`. If refresh succeeds, the new access token is stored via `createSession()` and the original request is retried. This happens transparently — the user is not logged out unless the refresh also fails.

**2. Edge Runtime Middleware (page loads)** — `proxy.ts`

When the access token is expired at the time of a page load, the middleware (running in Edge Runtime) detects this by decoding the JWT's `exp` claim. If a refresh token exists, it calls `POST /auth/refresh` directly, sets the new access token cookie on the response, and allows the request to proceed. If refresh fails, the user is redirected to `/login`.

This two-layer refresh ensures users stay authenticated even when returning to the app after the access token has expired — without needing to re-login.

### Shared Refresh Logic

The `refreshAccessToken()` function in `lib/auth.ts` is shared between `api-client.ts` (Route Handler context) and `proxy.ts` (Edge Runtime context). It performs the HTTP call to `POST /auth/refresh` and returns tokens, but does not persist them — each caller handles persistence according to its runtime constraints:

- `api-client.ts` → uses `createSession()` (Route Handler, can use `next/headers`)
- `proxy.ts` → sets cookies directly on `NextResponse` (Edge Runtime, uses Web APIs)

### Logout

`lib/session.ts` `deleteSession()` clears both cookies. The server-side refresh token remains valid in the database until explicitly revoked or until its 7-day expiry.

## Frontend Auth State

The frontend manages authentication state in the shared layout or a dedicated auth context. On page load, the layout checks for a valid session and populates the user state accordingly.

## Related Modules

- `genesis_frontend/proxy.ts` — Edge Runtime middleware; intercepts all requests, checks auth, handles token refresh on page loads
- `genesis_frontend/lib/auth.ts` — `authenticateUser()`, `fetchUser()`, `validateCredentials()`, `refreshAccessToken()` — auth utilities shared by server actions and middleware
- `genesis_frontend/lib/session.ts` — `createSession()`, `getAccessToken()`, `deleteSession()` — cookie management (Route Handler only, not Edge)
- `genesis_frontend/lib/api-client.ts` — `apiFetch()` — proxy-based API calls with automatic token refresh on 401
- `genesis_frontend/app/actions/auth.ts` — Server actions for login, logout, register
- `genesis_frontend/app/dashboard/layout.tsx` — Calls `getCurrentUser()` on every page load for auth checks

## Cookie Implementation

Session cookies are set by `lib/session.ts`. The `secure` flag is determined by the actual request protocol (`x-forwarded-proto` header), not `NODE_ENV`, to support HTTP access in development and via Tailscale tunnels.

> **Historical bug:** See [Gotchas](../developer_guides/gotchas.md) for a painful cookie `secure` flag issue encountered when deploying via Tailscale.
