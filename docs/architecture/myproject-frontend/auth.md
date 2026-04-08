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

When the access token expires (after 15 minutes), `apiFetch` in `lib/api-client.ts` automatically sends the refresh token to `POST /auth/refresh` and stores the new access token via `createSession()`. This happens transparently — the user is not logged out unless the refresh also fails.

### Logout

`lib/session.ts` `deleteSession()` clears both cookies. The server-side refresh token remains valid in the database until explicitly revoked or until its 7-day expiry.

## Frontend Auth State

The frontend manages authentication state in the shared layout or a dedicated auth context. On page load, the layout checks for a valid session and populates the user state accordingly.

## Related Modules

- `myproject_frontend/lib/auth.ts` — `authenticateUser()`, `fetchUser()`, `validateCredentials()` — called by server actions
- `myproject_frontend/lib/session.ts` — `createSession()`, `getAccessToken()`, `deleteSession()` — cookie management
- `myproject_frontend/lib/api-client.ts` — `apiFetch()` — proxy-based API calls with automatic token refresh
- `myproject_frontend/app/actions/auth.ts` — Server actions for login, logout, register
- `myproject_frontend/app/dashboard/layout.tsx` — Calls `getCurrentUser()` on every page load for auth checks

## Cookie Implementation

Session cookies are set by `lib/session.ts`. The `secure` flag is determined by the actual request protocol (`x-forwarded-proto` header), not `NODE_ENV`, to support HTTP access in development and via Tailscale tunnels.

> **Historical bug:** See [Gotchas](../developer_guides/gotchas.md) for a painful cookie `secure` flag issue encountered when deploying via Tailscale.
