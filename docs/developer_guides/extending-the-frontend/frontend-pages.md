# Frontend Pages Guide

This guide covers how to structure pages, manage scrolling, and size components correctly in the dashboard.

## The Single Scrollbar Rule

**Only one element on the page should scroll.** If you see two scrollbars, something is wrong.

The root layout already constrains the viewport:

```tsx
// app/layout.tsx
<body className="h-[100dvh] overflow-hidden">
```

And the dashboard layout enforces it further:

```tsx
// app/dashboard/layout.tsx
<SidebarProvider className="flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden">
  {/* Sidebar */}
  <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden">
    <header className="shrink-0 h-14 border-b" />
    <main className="flex-1 min-h-0 overflow-y-hidden flex flex-col">
      {children}
    </main>
  </div>
</SidebarProvider>
```

The `main` element uses `overflow-y-hidden` — it never scrolls. Scrolling is delegated to the page content inside `main`.

## PageContainer Variants

Use `PageContainer` with the correct variant to delegate scrolling appropriately.

### `dashboard` Variant (default)

For pages with standard scroll: task lists, project grids, data tables.

```tsx
<PageContainer variant="dashboard">
  <PageBody>
    {/* Content scrolls here. Max-width: 1600px. */}
  </PageBody>
</PageContainer>
```

The `dashboard` variant sets `overflow-y-auto` on the container — **this is the only scrollable element** on the page.

### `prose` Variant

For narrow-width content: forms, settings pages, articles.

```tsx
<PageContainer variant="prose">
  <PageBody>
    {/* Content scrolls here. Max-width: 5xl. */}
  </PageBody>
</PageContainer>
```

Same scrolling behavior as `dashboard` but narrower max-width.

### `app` Variant

For fixed-height pages where the page is locked to the viewport and internal sections scroll independently. Use for Chat, Sandbox, or any full-screen app.

```tsx
<PageContainer variant="app">
  <div className="shrink-0 h-14 border-b">Pinned Header</div>
  <div className="flex-1 min-h-0 overflow-y-auto">
    {/* This inner div scrolls — not the page */}
  </div>
  <div className="shrink-0 p-4 border-t">Pinned Footer</div>
</PageContainer>
```

**Critical**: `min-h-0` is required on the scrolling container. Without it, the flex child expands instead of scrolling.

**Critical**: Do **not** use `PageBody` with the `app` variant — the padding it applies will break the fixed-height layout.

## The `min-h-0` Rule

This is the most important and most commonly forgotten rule in the codebase.

When a flex container has `flex-direction: column` and an explicit height (like `h-full` or the viewport height from the layout), its children default to `min-height: auto` — meaning they will expand to fit their content. This breaks scrolling.

Adding `min-h-0` to a flex child overrides this default, telling the browser "this element can be smaller than its content, so clip it and scroll instead."

```tsx
// WRONG — the inner div expands instead of scrolling
<div className="flex flex-col h-full">
  <div className="overflow-y-auto">
    {/* This won't scroll — parent expands */}
  </div>
</div>

// CORRECT — min-h-0 allows the inner div to clip and scroll
<div className="flex flex-col h-full">
  <div className="flex-1 min-h-0 overflow-y-auto">
    {/* This scrolls correctly */}
  </div>
</div>
```

**Always add `min-h-0`** to:
- Any flex child that scrolls
- Any flex child that **contains** a scrolling element

## Server vs. Client Components

Next.js App Router distinguishes between server components and client components. This distinction is enforced at runtime — violating it causes hard errors.

### `'use client'` Directive

Any component that uses React hooks (`useState`, `useEffect`, `useContext`, etc.) **must** be a client component. Add `'use client'` at the very top of the file:

```typescript
'use client'

import { useState } from 'react'
export function MyComponent() {
  const [value, setValue] = useState(0)
  // ...
}
```

### The Hard Rule: Server Components Cannot Call Client Hooks

A server component is any `.tsx` file without `'use client'` at the top — including `page.tsx` files. Server components can **render** client components, but they cannot **call** client hooks.

Attempting to call a client hook (like `useChat()`) from a server component throws a runtime error:

```
Error: Attempted to call useChat() from the server.
useChat is a client function but was called from a server component.
```

**Wrong:**
```tsx
// app/dashboard/chats/[id]/page.tsx — this is a SERVER component
import { useChat } from '@/components/chat/chat-context'  // ❌ will crash

export default function ChatDetailPage() {
  const { tokenUsage } = useChat()  // ❌ calling client hook from server
  return <TokenBar data={tokenUsage} />
}
```

**Correct — pass data as props from server to client:**
```tsx
// app/dashboard/chats/[id]/page.tsx — SERVER component
export default async function ChatDetailPage() {
  const data = await getChatHistoryAction(sessionId)
  return (
    <ChatProvider initialTokenUsage={data.context_tokens}>
      <ChatWidget />  {/* ChatWidget is a CLIENT component that calls useChat() */}
    </ChatProvider>
  )
}
```

### Pattern Summary

| Situation | Approach |
|----------|----------|
| Page fetches data server-side | Use `page.tsx` as server component, pass data as props |
| Need React state (`useState`) | `'use client'` component |
| Need context (`useChat`, etc.) | `'use client'` component |
| New UI component with hooks | `'use client'` at top of file |
| Static display component (no hooks) | Can be server component, no `'use client'` needed |

**Rule of thumb**: If a component imports from `context.tsx` or uses `useState`/`useEffect`, it must be a client component. Place it inside the client component tree, not in the server page itself.

## PageContainer is the Root Rule

**Every page must have `PageContainer` as its single root element.** There are no siblings outside `PageContainer`. This rule ensures:

1. All page content is contained within the scroll/viewport management system
2. Horizontal alignment (via `chat-viewport-container`) is consistent across all components
3. No elements can accidentally break the flex/scroll hierarchy

```tsx
// ✅ CORRECT — PageContainer wraps everything
export default function MyPage() {
  return (
    <PageContainer variant="app">
      <header>Title</header>
      <ChatWidget />
    </PageContainer>
  )
}

// ❌ WRONG — sibling elements outside PageContainer
export default function MyPage() {
  return (
    <>
      <TokenBar />          {/* ❌ outside PageContainer — breaks layout */}
      <PageContainer variant="app">
        <ChatWidget />
      </PageContainer>
    </>
  )
}
```

If you need a UI element to appear above a page's content (e.g., a token bar, a notification banner), place it **inside** a client component that is already inside `PageContainer` — like `ChatWidget`. Never add elements as siblings to `PageContainer`.

## Visual Checklist for PR Reviews

Run through this checklist before submitting a PR:

- [ ] Does the page use `PageContainer`?
- [ ] Is there more than one vertical scrollbar on the screen? (There should only be one).
- [ ] Do headers stay pinned when scrolling?
- [ ] Is `min-h-0` present on flex-parents of scrolling areas?
- [ ] On mobile, is there at least `p-4` padding? (Handled automatically by `PageBody`.)
- [ ] Is `PageBody` **not** used inside an `app` variant?
- [ ] Do widths default to `w-full` rather than hardcoded pixel values?
- [ ] Do heights use `h-full` rather than fixed pixel values?

## Common Mistakes

### Double scrollbar

Usually caused by adding `overflow-y-auto` to both `PageContainer` and an inner element. The `dashboard` and `prose` variants already set `overflow-y-auto` on the outer container.

**Fix**: Remove `overflow-y-auto` from inner elements when using `dashboard`/`prose` variants.

### Content doesn't scroll

Usually caused by missing `min-h-0` on the flex parent of the scrolling element.

**Fix**: Add `min-h-0` to the flex parent.

### `app` variant content overflows

Usually caused by using `PageBody` inside an `app` variant. The padding from `PageBody` adds height that overflows the fixed viewport.

**Fix**: Don't use `PageBody` with `app`. Use raw `<div>` with manual padding instead.

## Module Reference

- `components/dashboard/page-container.tsx` — `PageContainer` and `PageBody` implementations
- `app/dashboard/layout.tsx` — Dashboard layout with sidebar and main content area
- `app/layout.tsx` — Root layout with viewport constraints
