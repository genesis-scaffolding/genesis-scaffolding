# Authentication Architecture

## Overview

This document describes how the system authenticates users and manages sessions across the FastAPI backend, Next.js frontend, and browser. It covers JWT token structure, the login and logout flows, token refresh, and the role of the Edge Middleware in protecting routes.

## Background: How Token-Based Authentication Works

### The basic idea

Instead of sending the password on every request, the server verifies the password once. On success it issues a token — a signed piece of data that proves the user has been authenticated. The client then sends this token on each subsequent request. The server validates the token and grants access without needing to check the password again.

### Login

1. The client sends the username and password to the server over HTTPS.
2. The server looks up the user and verifies the password hash.
3. If valid, the server creates an access token and returns it to the client.
4. The client stores the token and uses it for all following requests.

### Accessing protected resources

On every request, the client includes the access token in the `Authorization` header using the Bearer scheme:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

The server receives the request, reads the token, verifies the signature, and checks the expiry. If valid, the server knows who the user is from the token payload and processes the request. If the token is missing, malformed, or expired, the server returns HTTP 401 Unauthorized.

### Why 401 and not 403

403 Forbidden means the server recognized the user but the user does not have permission for that specific resource. 401 Unauthorized means the server does not know who the user is — authentication failed or was not attempted. JWT authentication uses 401 for missing or invalid tokens.

### The problem with long-lived access tokens

Access tokens are kept short-lived because if one is leaked or stolen, an attacker can impersonate the user only until the token expires. A short window limits the damage. But asking users to re-enter their password every 15 minutes is a poor experience.

### Refresh tokens

The solution is to issue two tokens on login. The access token is short-lived (e.g., 15 minutes). A second token called the refresh token has a much longer expiry (e.g., 7 days). When the access token expires, the client presents the refresh token to the server to obtain a new access token without asking for the password again. The user stays logged in as long as the refresh token is valid.

## JWT Token Structure

A JWT token has three parts separated by dots:

```
header.payload.signature
```

**Header** — JSON describing the algorithm used to sign the token. Base64-encoded.

**Payload** — JSON containing the token data. The server puts a username or user ID in a field called `sub` (subject). An `exp` field marks when the token expires. A `type` field can distinguish access tokens from refresh tokens. Base64-encoded.

**Signature** — A mathematical proof produced by running a hashing algorithm on `header.payload` using a secret key known only to the server. This proves the token was created by the server and was not modified since.

The payload is plain Base64 text — anyone can decode it and read the username and expiry. The signature is what prevents forgery. Without the secret key, no one can produce a valid signature for a different username or a different expiry. When the server receives a token, it runs the same algorithm using its secret key and checks whether the result matches the signature provided.

## System Architecture and Data Flow

### Three processes

The system runs on three separate processes:

- **FastAPI backend** — listens on port 8000. Handles all API requests, token issuance, and database operations.
- **Next.js server** — listens on port 3000. Serves pages and static assets to the browser, runs server components and server actions, and forwards API calls to FastAPI.
- **Browser** — runs React JavaScript code downloaded from the Next.js server. Interacts with the user and makes requests back to the Next.js server.

### How the browser communicates

The browser never talks to FastAPI directly. Every request from the browser goes to the Next.js server on port 3000. There are two paths:

- **Page requests and server actions** — the browser requests pages or submits forms. Next.js handles these directly.
- **API calls** — the browser calls `/api/...`. Next.js forwards these to FastAPI and returns the response. The forwarding code (in `app/api/[...proxy]/route.ts`) adds the access token from the browser cookie to the `Authorization: Bearer` header before forwarding. This step is what prevents FastAPI from returning 401.

### Where the Edge Middleware runs

The Edge Middleware (`proxy.ts`) runs inside the Next.js process, on every incoming request before it reaches any route or page. It intercepts requests, checks the access token expiry, and handles refresh or redirect before the request proceeds.

### Browser cookies

After login, the browser holds two cookies set by the Next.js server: `access_token` and `refresh_token`. Both are httpOnly — JavaScript running in the browser tab cannot read their contents. The browser sends them automatically on every request to the Next.js server.

## Login Flow

### Step 1 — user submits the form

The user fills in the login form and submits. The browser POSTs the form to `loginAction`, which is a Next.js server action running on the Next.js server.

### Step 2 — Next.js server calls FastAPI

`loginAction` calls `authenticateUser()` which POSTs the credentials directly to FastAPI at `http://localhost:8000/auth/login`. This call happens from the Next.js server, not the browser.

FastAPI receives the request, verifies the password against the stored hash, and if valid returns a JSON response containing:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900,
  "token_type": "bearer"
}
```

### Step 3 — Next.js server sets cookies

Back in `loginAction`, the tokens from FastAPI are passed to `createSession()`. This calls the Next.js `cookies()` API to set two httpOnly cookies on the response that will be sent back to the browser:

- `access_token` — maxAge set to the value of `expires_in` (about 15 minutes)
- `refresh_token` — maxAge set to 7 days

The `secure` flag on both cookies is set based on the `x-forwarded-proto` request header. If the connection is HTTPS, `secure: true` is set. This lets the system work over both HTTP and HTTPS depending on the deployment setup.

### Step 4 — browser receives cookies

The Next.js server sends its response to the browser. The browser stores the two cookies automatically. The browser then navigates to `/dashboard` as directed by the login form client-side code.

```mermaid
sequenceDiagram
    participant Browser
    participant LoginForm as LoginForm<br/>(client component)
    participant loginAction as loginAction<br/>(server action)
    participant authenticateUser as authenticateUser<br/>(lib/auth.ts)
    participant FastAPI as FastAPI<br/>/auth/login
    participant createSession as createSession<br/>(lib/session.ts)

    Browser->>LoginForm: submits form (username, password)
    LoginForm->>loginAction: POST form data

    rect rgb(245, 248, 255)
        Note over loginAction,FastAPI: Runs on Next.js server process
        loginAction->>authenticateUser: username, password
        authenticateUser->>FastAPI: POST /auth/login<br/>Content-Type: application/x-www-form-urlencoded
        FastAPI->>FastAPI: verify password hash
        FastAPI-->>authenticateUser: TokenResponse<br/>(access_token, refresh_token, expires_in)
        authenticateUser-->>loginAction: success, TokenResponse
    end

    loginAction->>createSession: access_token, refresh_token, expires_in

    rect rgb(240, 255, 245)
        Note over createSession: Sets httpOnly cookies on HTTP response
        createSession->>Browser: HTTP response with Set-Cookie headers
    end

    Browser->>Browser: router.push("/dashboard")
```

## Authentication Check on Every Request

Every request from the browser passes through two authentication checkpoints before it succeeds.

### Checkpoint 1 — Edge Middleware

The Edge Middleware (`proxy.ts`) runs first, before the request reaches any page or API route. It reads the `access_token` cookie, decodes the JWT payload to read the `exp` field, and checks if the token has expired.

```mermaid
sequenceDiagram
    participant Browser
    participant proxy as proxy.ts<br/>(Edge Middleware)
    participant refreshAccessToken as refreshAccessToken<br/>(lib/auth.ts)
    participant FastAPI as FastAPI<br/>/auth/refresh
    participant NextResponse as NextResponse

    Browser->>proxy: GET /dashboard<br/>Cookie: access_token=..., refresh_token=...
    proxy->>proxy: decode JWT payload, read exp

    alt access token not expired
        proxy->>NextResponse: NextResponse.next()
        NextResponse-->>Browser: proceed to page
    else access token expired, refresh token present
        proxy->>refreshAccessToken: refreshToken
        refreshAccessToken->>FastAPI: POST /auth/refresh<br/>{ refresh_token }
        alt refresh succeeds
            FastAPI-->>refreshAccessToken: TokenResponse
            refreshAccessToken-->>proxy: TokenResponse
            proxy->>NextResponse: set new access_token cookie
            NextResponse-->>Browser: proceed to page with fresh token
        else refresh fails
            refreshAccessToken-->>proxy: null
            proxy->>NextResponse: delete cookies, redirect /login
            NextResponse-->>Browser: 302 redirect /login
        end
    else no access token, not a public path
        proxy->>NextResponse: delete cookies, redirect /login
        NextResponse-->>Browser: 302 redirect /login
    end
```

There are three possible outcomes:

- **Token is valid and not expired** — the request proceeds.
- **Token is expired but a refresh token exists** — the middleware calls `POST /auth/refresh` to get a new access token, sets the new access token cookie on the response, and lets the request proceed. If refresh fails, cookies are deleted and the browser is redirected to `/login`.
- **No access token and not a public path** — cookies are deleted and the browser is redirected to `/login`.

The middleware only reads the expiry from the JWT payload — it does not verify the signature. Signature verification is done by FastAPI.

### Checkpoint 2 — FastAPI

When a request reaches FastAPI (either a page request forwarded through the proxy, or an API call), FastAPI reads the token from the `Authorization: Bearer` header. It decodes the JWT and verifies the signature using the secret key. It also checks the `exp` claim.

```mermaid
sequenceDiagram
    participant Browser
    participant proxyRoute as app/api/[...proxy]/<br/>route.ts
    participant FastAPI as FastAPI<br/>/users/me
    participant dashboardLayout as app/dashboard/<br/>layout.tsx

    rect rgb(245, 248, 255)
        Note over proxyRoute,FastAPI: API call path (via proxy route)
        Browser->>proxyRoute: GET /api/users/me
        proxyRoute->>proxyRoute: read access_token cookie<br/>set Authorization: Bearer <token>
        proxyRoute->>FastAPI: GET /users/me<br/>Authorization: Bearer ...
        FastAPI->>FastAPI: verify JWT signature, check exp
        alt token valid
            FastAPI-->>proxyRoute: 200 User JSON
            proxyRoute-->>Browser: JSON response
        else token invalid or expired
            FastAPI-->>proxyRoute: 401 Unauthorized
            proxyRoute-->>Browser: 401 JSON
        end
    end

    rect rgb(255, 250, 240)
        Note over dashboardLayout,FastAPI: Page load path (server component)
        Browser->>dashboardLayout: GET /dashboard/tasks
        dashboardLayout->>dashboardLayout: call getCurrentUser()
        dashboardLayout->>FastAPI: GET /users/me<br/>(direct fetch, no proxy)
        FastAPI->>FastAPI: verify JWT signature, check exp
        alt token valid
            FastAPI-->>dashboardLayout: 200 User JSON
            dashboardLayout-->>Browser: render page
        else token invalid
            FastAPI-->>dashboardLayout: 401
            dashboardLayout->>Browser: redirect /login
        end
    end
```

If the signature is valid and the token has not expired, FastAPI processes the request. If the token is missing, the signature is invalid, or the token has expired, FastAPI returns HTTP 401.

The dashboard layout (`app/dashboard/layout.tsx`) is a server component. On every page load it calls `getCurrentUser()`, which reads the access token cookie and calls `GET /users/me`. If this call returns a valid user, the page renders. If it returns 401, the layout redirects to `/login`.

This second check can fail even when the middleware allowed the request through — for example if the JWT secret has changed since the token was issued.

## Token Refresh

There are two contexts in which the refresh flow runs. Both use the same `refreshAccessToken()` function, which calls `POST /auth/refresh` with the refresh token and returns a new access token if the refresh token is valid.

### Refresh in the Edge Middleware

```mermaid
sequenceDiagram
    participant proxy as proxy.ts<br/>(Edge Middleware)
    participant refreshAccessToken as refreshAccessToken<br/>(lib/auth.ts)
    participant FastAPI as FastAPI<br/>/auth/refresh
    participant NextResponse as NextResponse

    proxy->>proxy: access token expired
    proxy->>refreshAccessToken: refreshToken
    refreshAccessToken->>FastAPI: POST /auth/refresh<br/>{ refresh_token }
    alt refresh succeeds
        FastAPI-->>refreshAccessToken: TokenResponse<br/>(access_token, expires_in)
        refreshAccessToken-->>proxy: TokenResponse
        proxy->>NextResponse: set new access_token cookie
        proxy->>NextResponse: NextResponse.next()
    else refresh fails
        refreshAccessToken-->>proxy: null
        proxy->>NextResponse: delete cookies, redirect /login
    end
```

This runs proactively before a page request. The middleware detects an expired access token, calls `/auth/refresh`, sets the new access token cookie on the `NextResponse`, and lets the request proceed. The browser gets a fresh access token without any visible interruption.

### Refresh in apiFetch

```mermaid
sequenceDiagram
    participant Browser
    participant apiFetch as apiFetch<br/>(lib/api-client.ts)
    participant refreshAccessToken as refreshAccessToken<br/>(lib/auth.ts)
    participant createSession as createSession<br/>(lib/session.ts)
    participant deleteSession as deleteSession<br/>(lib/session.ts)
    participant FastAPI as FastAPI<br/>/auth/refresh

    Browser->>apiFetch: GET /api/chats<br/>Cookie: access_token=...
    apiFetch->>FastAPI: GET /api/chats<br/>Authorization: Bearer <token>
    FastAPI-->>apiFetch: 401 Unauthorized

    alt refresh succeeds
        apiFetch->>refreshAccessToken: refreshToken
        refreshAccessToken->>FastAPI: POST /auth/refresh<br/>{ refresh_token }
        FastAPI-->>refreshAccessToken: TokenResponse<br/>(access_token, expires_in)
        refreshAccessToken-->>apiFetch: TokenResponse
        apiFetch->>createSession: new_access_token, refresh_token, expires_in
        createSession-->>Browser: HTTP response with new Set-Cookie
        apiFetch->>FastAPI: retry GET /api/chats<br/>Authorization: Bearer new_token
        FastAPI-->>apiFetch: 200
        apiFetch-->>Browser: JSON response
    else refresh fails
        apiFetch->>deleteSession: (clear cookies)
        deleteSession-->>Browser: HTTP response (cookies deleted)
        apiFetch-->>Browser: 401
    end
```

This runs reactively when an API call returns 401. `apiFetch` catches the 401, calls `/auth/refresh`, and if successful updates both cookies via `createSession()` and retries the original request. If refresh fails, `deleteSession()` clears the cookies.

Both contexts call the same FastAPI endpoint. The difference is the runtime environment (Edge vs Route Handler) and how the response is handled (set cookie on `NextResponse` vs call `createSession()`).

## Logout

Logout is straightforward. `deleteSession()` deletes the `access_token` and `refresh_token` cookies from the browser. The browser then has no tokens, so subsequent requests fail the middleware check and redirect to `/login`.

There is no server-side token revocation. The refresh token remains valid in the browser until it expires — if the cookies are accidentally restored (e.g., from a browser backup), the session would be reactivated. The FastAPI server also does not delete or invalidate the refresh token on logout. The token is only invalidated when it expires.

## Known Limitations and Planned Improvements

### No server-side token revocation

Refresh tokens cannot be invalidated before they expire. If cookies are accidentally restored from a browser backup, or if a refresh token is stolen before expiry, the session can be reactivated or hijacked. The only mitigation currently is the short access token window. Planned fix: store refresh tokens in the database and delete them on logout.

### JWT secret sensitivity causes login loops

All outstanding tokens become invalid if the FastAPI server restarts with a different `JWT_SECRET_KEY`. The Edge Middleware only checks the expiry in the JWT payload — it lets structurally valid tokens through. FastAPI then rejects them because the signature was signed with a different secret. This produces the observed loop: the middleware allows the page to load, the dashboard server component calls `/users/me`, FastAPI returns 401, and the user is redirected back to login. Fix: either store issued tokens in the database with a reference count, or treat the JWT secret as an immutable deployment configuration.

### Inconsistent refresh failure behavior

When token refresh fails, the Edge Middleware deletes cookies and redirects to `/login`. The `apiFetch` interceptor deletes cookies and returns the 401 to the caller. Depending on where the failure occurs, the user either sees a redirect or a blank error. These should behave consistently.

### Middleware does not verify JWT signature

The Edge Middleware only decodes the expiry from the JWT payload. It does not verify the signature. A structurally valid token that was signed with a different secret (e.g., from a previous server instance) will pass the middleware but fail at FastAPI. This is the root cause of the login loop described above. Fix: the middleware should call FastAPI to validate the token, or FastAPI should expose a lightweight validation endpoint.

### No token rotation

The refresh token is reused on every refresh. If a refresh token is stolen, it remains valid for its full 7-day lifespan. Best practice is to issue a new refresh token on each refresh (token rotation) and invalidate the old one. This limits the window of exposure if a token is compromised.

### No rate limiting on refresh endpoint

`POST /auth/refresh` has no rate limiting. An attacker with a valid refresh token could make unlimited requests to obtain new access tokens. Mitigation: add rate limiting to the refresh endpoint.