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

---

## Backend `datetime` → JavaScript Date Comparisons

### The Problem

Backend `datetime.now(UTC).isoformat()` strips the `Z` suffix, producing strings like `"2026-04-07T01:33:11"` without timezone info. When parsed in JavaScript with `new Date(...)`, this is interpreted as **local time** — not UTC.

This causes comparison bugs when the user's browser is in a timezone other than UTC (e.g., UTC+10:30 Adelaide). For example:

```typescript
// Backend: updated_at = "2026-04-07T01:33:11" (stored as UTC, but isoformat() drops the Z)
// JavaScript parses this as local time: 2026-04-07T01:33:11+10:30
// Date.now() returns UTC:                           2026-04-07T11:33:11Z
// Comparison sees the session as ~10 hours old, not 10 minutes old
```

### The Fix

When comparing a backend datetime field in JavaScript, append `'Z'` to force UTC parsing:

```typescript
// WRONG — parses as local time
const updatedAt = new Date(session.updated_at);

// CORRECT — parses as UTC
const updatedAt = new Date(session.updated_at + 'Z');
```

This applies to any backend datetime stored as UTC and serialized via `.isoformat()`.

---

## `apiFetch` vs Raw `fetch` in Server Actions

### The Problem

In Next.js server actions (functions marked `'use server'`), `fetch` requires an **absolute URL** — relative URLs like `/api/chats` will fail. In client components, browser `fetch` handles relative URLs fine.

The project's `apiFetch` helper (`@/lib/api-client`) sends requests through the Next.js proxy at `/api/*`, which forwards to FastAPI. Using raw `fetch` with a relative path will fail at runtime in server actions.

### The Fix

```typescript
// WRONG — fails in server actions (Node.js fetch needs absolute URL)
const res = await fetch('/api/chats', { method: 'POST', ... });

// CORRECT — routes through Next.js proxy to FastAPI
const res = await apiFetch('/chats/', { method: 'POST', ... });
```

### When to Use Each

| Context | Use |
|---|---|
| Server actions (`'use server'`) | `apiFetch('/chats/...')` — routes through proxy |
| Client components | `apiFetch('/chats/...')` — also routes through proxy |
| External URLs (e.g., webhooks) | Raw `fetch` with absolute URL |

Note: The existing `StartChatButton` in `components/dashboard/start-chat-button.tsx` uses raw `fetch('/api/chats', ...)` — this works only because it is a client component, not a server action. It should be migrated to use `apiFetch` for consistency.

---

## SSE `_broadcast` Wrapper Buries Event Data One Level Deep

### The Problem

All SSE events from `ActiveRun._broadcast()` share the same envelope format:

```python
payload = {"event": event, "data": data, "index": index}
```

This means `data` is **always one level inside** the parsed object, not at the top level. Frontend handlers that destructure directly from `JSON.parse(e.data)` work correctly for events where `data` is a primitive (e.g., `content` events where `data` is a string). But handlers that treat `data` as a top-level object get the wrapper instead.

Example — `token_usage` was doing:
```typescript
eventSource.addEventListener('token_usage', (e) => {
  setTokenUsage(JSON.parse(e.data)); // WRONG: sets {data: {...token_info...}, index: null}
});
```

Instead of:
```typescript
eventSource.addEventListener('token_usage', (e) => {
  const parsed = JSON.parse(e.data);
  setTokenUsage(parsed.data ?? parsed); // Correct: unwraps or falls back
});
```

### Why It Hid for So Long

During streaming, the 10fps throttle only calls `setDisplayActiveMessages()` — `TokenBar` does not re-render. So even though `setTokenUsage` was corrupting state with the wrapped object, the broken values were never displayed.

When the SSE connection ends, `refreshHistory()` fetches fresh data from the DB and calls `setTokenUsage` again with the correct server values, overwriting the corrupted state before `TokenBar` ever renders.

The bug only surfaced when a new SSE event (`clipboard`) triggered a re-render of `ChatWidget` while `isRunning` was still `true` — bypassing `refreshHistory()` and exposing the corrupted `tokenUsage` state.

### The Fix

Always unwrap `parsed.data` for events that carry objects, not primitives:

```typescript
setTokenUsage(parsed.data ?? parsed);   // for token_usage
setClipboardMd(parsed.data?.clipboard_md ?? null);  // for clipboard
```

Or consistently destructure with `const { data, index } = parsed` for all events, then use `data` directly.

### Lesson

SSE event handlers that process non-string data must account for the `_broadcast` wrapper. Any new SSE event type should be tested by forcing a re-render mid-stream (e.g., add a state setter for an unrelated piece of state in the handler) to catch these mismatches early.

---

## Timezone Lost Through Agent → AgentMemory → AgentClipboard Chain

### Symptoms

- User sets their timezone (e.g., `America/New_York`)
- The agent correctly uses the timezone when injecting clipboard into the LLM prompt (function calls render timestamps in the correct timezone)
- But the clipboard content sent to the browser via `chat.py` renders timestamps in UTC instead of the user's timezone
- The user sees incorrect timestamps in the chat UI despite the agent working correctly internally

### Root Cause

The `timezone` parameter was not being propagated through the initialization chain:

1. `Agent.__init__()` accepted `timezone` and passed it to `AgentMemory`
2. `AgentMemory.__init__()` accepted `timezone` but did NOT pass it to `AgentClipboard` when creating the default clipboard
3. `AgentClipboard` had no `timezone` field, so `render_to_markdown()` used UTC hardcoded

When `chat.py` called `agent.memory.agent_clipboard.render_to_markdown()`, the clipboard had no knowledge of the user's timezone.

### The Fix

Three files were modified:

**`myproject-core/src/myproject_core/agent.py`** — Pass `timezone` to `AgentMemory` constructor:
```python
self.memory = memory or AgentMemory(
    messages=[self._create_llm_message(role="system", content=system_prompt)],
    timezone=timezone  # Added
)
```

**`myproject-core/src/myproject_core/agent_memory.py`** — Accept and forward `timezone` to `AgentClipboard`:
```python
def __init__(self, messages=None, agent_clipboard=None, timezone: str = "UTC") -> None:
    self.agent_clipboard = agent_clipboard or AgentClipboard(timezone=timezone)
    self.timezone = timezone
```

And when resetting clipboard:
```python
def reset_memory(self):
    self.messages = []
    self.agent_clipboard = AgentClipboard(timezone=self.timezone)  # Preserves timezone
```

**`myproject-core/src/myproject_core/schemas.py`** — Add `timezone` field to `AgentClipboard`:
```python
class AgentClipboard(BaseModel):
    timezone: str = "UTC"  # Added
```

And in `render_to_markdown()`, use the instance's timezone instead of hardcoded UTC:
```python
if self.timezone:
    timezone = self.timezone
```

### Lesson

When a parameter flows through multiple layers of object construction, ensure it is explicitly propagated at each step. A timezone that is correctly used at one layer (LLM context) can be silently lost if the intermediate layers don't forward it. Always trace parameter flow from construction to final use — the symptom (wrong timezone in browser) was far removed from the cause (AgentMemory not forwarding timezone to AgentClipboard).

---

## `pathlib.Path.absolute()` Does Not Resolve `..` Components

### Symptoms

- `LocalSandboxFilesystem._resolve("../../../etc/passwd")` did not raise — traversal was allowed
- `_resolve("some/../../other")` also bypassed the sandbox boundary check
- But symlinks were correctly followed and rejected when they escaped

### Root Cause

`Path.absolute()` does NOT resolve `..` or `.` path components. It only converts a relative path to an absolute one without traversing symlinks:

```python
>>> from pathlib import Path
>>> joined = Path('/tmp/sandbox') / '../../../etc/passwd'
>>> joined.absolute()
Path('/tmp/sandbox/../../../etc/passwd')  # still has .. components
>>> joined.absolute().is_relative_to(Path('/tmp/sandbox'))
True  # incorrect! /etc/passwd is NOT inside /tmp/sandbox
```

`Path.resolve()` does resolve `..` components, but it **also resolves symlinks**, which breaks the sandbox's ability to preserve symlink structure (e.g., `knowledge-base` → external directory).

### The Fix

Use `os.path.normpath(os.path.abspath(str(joined)))` instead:

```python
import os

normalized = Path(os.path.normpath(os.path.abspath(str(joined))))
# os.path.abspath() resolves symlinks too, but normpath strips the extra bits
# os.path.normpath() collapses .. and . components WITHOUT following symlinks
# Together they give a normalized absolute path that is safe to check against sandbox
```

The combination works because:

- `os.path.abspath()` converts to absolute path but also normalizes (collapses `..`)
- `os.path.normpath()` then cleans up any remaining `.` and `..` components
- Neither function (alone or together) resolves symlinks the way `Path.resolve()` does

This lets the sandbox:
1. Detect real path traversal (`../../../etc/passwd`) by checking the normalized path
2. Preserve symlink structure for paths inside the sandbox (so `get_subdirectories` returns `knowledge-base/docs`, not `/external/drive/docs`)
3. Still detect when a symlink inside the sandbox points outside (when `allow_symlinks_outside=False`)

### Lesson

`Path.absolute()` is NOT equivalent to "normalized absolute path". It preserves `..` components that `is_relative_to()` cannot detect. Always use `os.path.normpath(os.path.abspath(...))` when normalizing user-supplied relative paths before boundary checks.

