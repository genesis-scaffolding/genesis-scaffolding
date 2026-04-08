# Painful Bugs We Solved

A log of bugs, their symptoms, root causes, and fixes. Updated as problems are discovered and solved.

---

## 2026-04-08: Cookie `secure` Flag Breaking Login via Tailscale HTTP

### Symptoms

- Login works from `localhost` on the same machine
- Login fails from a phone via Tailscale (same network, accessing via tailnet address)
- On the phone, after entering correct credentials, the browser redirects back to login
- Server-side logs show successful token generation (access + refresh tokens issued)
- Middleware logs show subsequent `/dashboard` request has no cookies at all
- Dev mode (`next dev`) works fine; production mode (`next start` via `make run`) fails

### Root Cause

In `lib/session.ts`, session cookies were set with:

```typescript
secure: process.env.NODE_ENV === 'production',
```

In production mode, `NODE_ENV === 'production'` is `true`, so `secure: true` was set on cookies. Browsers refuse to send `secure: true` cookies over HTTP — they require HTTPS.

When accessing via Tailscale with `http://tail-address:3000`, the request is HTTP, so the browser discarded the `secure: true` cookies and never sent them back.

In dev mode, `secure: false`, so cookies worked over HTTP.

### The Fix

Changed `lib/session.ts` to detect the actual request protocol instead of relying on `NODE_ENV`:

```typescript
import { cookies, headers } from 'next/headers';

export async function createSession(accessToken: string, refreshToken: string, expiresIn: number) {
  const cookieStore = await cookies();
  const headersList = await headers();
  // Check if request is over HTTPS (including behind reverse proxies)
  // x-forwarded-proto is set by most reverse proxies (nginx, tailscale exit node, etc.)
  const forwardedProto = headersList.get('x-forwarded-proto') || 'http';
  const isHttps = forwardedProto === 'https';
  // Only set secure=true if actually over HTTPS, not just because NODE_ENV=production
  // This allows HTTP access in production when behind reverse proxies or direct connections

  cookieStore.set('access_token', accessToken, {
    httpOnly: true,
    secure: isHttps,
    sameSite: 'lax',
    maxAge: expiresIn,
    path: '/',
  });

  cookieStore.set('refresh_token', refreshToken, {
    httpOnly: true,
    secure: isHttps,
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: '/',
  });
}
```

### Lesson

Never set `secure: true` based solely on `NODE_ENV`. Always detect the actual protocol of the incoming request via `x-forwarded-proto` or similar headers. The `NODE_ENV=production` heuristic assumes HTTPS everywhere, which is not true when accessing via Tailscale or other HTTP tunnels.
