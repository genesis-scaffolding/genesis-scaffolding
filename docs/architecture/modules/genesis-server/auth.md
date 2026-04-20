# Authentication Architecture

## Overview

The system uses JWT-based authentication to secure communication between the FastAPI server and the NextJS frontend. Tokens are stateless — the server validates them cryptographically without querying a database — while per-user data access is stateful: each authenticated request opens the calling user's specific SQLite database file. This separation keeps token handling lightweight and horizontal scaling straightforward, while preserving strict per-user data isolation.

## Password Authentication

User passwords are hashed using Argon2id via the pwdlib library, which provides memory-hard hashing resistant to GPU and hardware-accelerated attacks. The auth module exposes an OAuth2 password flow endpoint. When a client submits credentials, the server verifies the password hash and returns token pairs.

## Token Strategy

The system issues two classes of tokens:

**Access tokens** are short-lived JWTs (15-minute expiry) used to authorize API requests. They contain a minimal payload: a subject claim identifying the user, an issued-at timestamp, and an expiry time. The access token payload deliberately omits permissions or roles; authorization decisions are derived from the user context injected per-request.

**Refresh tokens** are long-lived tokens (7-day expiry) used solely to obtain new access tokens. They are not JWTs but opaque tokens stored in the user's SQLite database, allowing server-side revocation if needed. A refresh token can be exchanged for a new access token via the refresh endpoint without requiring the user to re-authenticate with their password.

## Per-Request Dependency Injection

FastAPI's dependency injection system handles auth on every authenticated endpoint. The `get_current_active_user()` dependency decodes the JWT access token from the incoming request's `Authorization` header, verifies the signature against the server's secret, validates expiry, and extracts the subject claim. The decoded user identifier is then used to open that user's dedicated SQLite file, and the resulting user context object is injected into the route handler.

## Multi-User Isolation

The JWT payload identifies the user via the subject claim. When the dependency injection decodes this claim, it resolves it to a specific user record and opens the corresponding SQLite file. This file contains the user's refresh token, conversation history, agent memory, and all other per-user data. No request can access another user's data unless that user's JWT subject is explicitly requested, which does not occur in normal operation.

## Refresh Flow

When an access token expires, the client sends the long-lived refresh token to `POST /auth/refresh`. The server looks up the refresh token in the requesting user's SQLite file, verifies it has not been revoked or expired, and if valid issues a new access token with a fresh 15-minute expiry. The refresh token itself is not replaced during this flow; only the access token is renewed. This allows clients to maintain a session indefinitely by refreshing before expiry, while the short access token window limits the exposure if a token is leaked.

## Related Modules

- `genesis_server.auth` — Auth service (password hashing, token generation)
- `genesis_server.dependencies` — JWT decoding and user injection (`get_current_user`, `get_current_active_user`)
- `genesis_server.routers.auth` — Auth endpoints (login, refresh, logout)
