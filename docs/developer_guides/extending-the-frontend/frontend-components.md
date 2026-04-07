# Frontend Components Guide

This guide explains how to integrate new backend entities into the frontend UI.

## Frontend Overview

The frontend is a **Next.js** project using the App Router.

### Tech Stack

- **Framework**: React (App Router)
- **UI Components**: Shadcn UI
- **Icons**: Lucide-react
- **Styling**: Tailwind CSS / PostCSS

### Key Directories

| Path | Description |
|---|---|
| `app/actions/` | Server Actions for data fetching and mutations |
| `app/api/[...proxy]/` | API proxy route (forwards to FastAPI) |
| `app/dashboard/` | Dashboard pages and layouts |
| `components/dashboard/` | Dashboard-specific components |
| `types/` | TypeScript interface definitions |
| `lib/` | Shared utilities including `api-client.ts` |

## Page Layout System

The most important components for page layout are `PageContainer` and `PageBody`, both defined in `components/dashboard/page-container.tsx`. These enforce consistent width, scrolling, and spacing across all dashboard pages.

### PageContainer

`PageContainer` wraps page content and manages scroll behavior based on the `variant` prop:

```typescript
// components/dashboard/page-container.tsx
type PageVariant = "prose" | "dashboard" | "app";

const PageContainer = React.forwardRef<HTMLDivElement, PageContainerProps>(
  ({ variant = "dashboard", children, className, ...props }, ref) => {
    const scrollerStyles: Record<PageVariant, string> = {
      prose: "overflow-y-auto w-full flex-1",
      dashboard: "overflow-y-auto w-full flex-1",
      app: "overflow-hidden flex flex-col w-full flex-1", // App variant doesn't scroll at this level
    };

    const innerStyles: Record<PageVariant, string> = {
      prose: "max-w-5xl mx-auto w-full min-h-full",
      dashboard: "max-w-[1600px] mx-auto w-full min-h-full",
      app: "max-w-none w-full h-full flex flex-col",
    };

    return (
      <div ref={ref} className={cn("h-full min-h-0 min-w-0", scrollerStyles[variant], className)} {...props}>
        <div className={innerStyles[variant]}>
          {children}
        </div>
      </div>
    );
  }
);
```

### PageBody

`PageBody` provides standard padding and vertical spacing. It should **not** be used inside the `app` variant:

```typescript
const PageBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("flex flex-col p-4 md:p-6 lg:p-10", className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
```

### Variant Reference

| Variant | Max Width | Scroll Behavior | PageBody | Use Case |
|---|---|---|---|---|
| **`dashboard`** | `max-w-[1600px]` | Page-level scroll | Yes | Tables, grids, lists |
| **`prose`** | `max-w-5xl` | Page-level scroll | Yes | Forms, settings, articles |
| **`app`** | none | Fixed height, internal scroll only | **No** | Chat, sandbox, canvas |

## Dashboard Layout Structure

The dashboard layout (`app/dashboard/layout.tsx`) constrains the entire viewport:

```tsx
// app/dashboard/layout.tsx
<SidebarProvider className="flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden">
  <Sidebar />
  <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden">
    <header className="shrink-0 h-14 border-b" />  {/* Pinned header */}
    <main className="flex-1 min-h-0 overflow-y-hidden flex flex-col">
      {children}
    </main>
  </div>
</SidebarProvider>
```

Key rules enforced by the layout:
- The **browser window never scrolls** — `h-[100dvh] overflow-hidden` on `body`
- The **main content area** (`main`) uses `flex-1 min-h-0 overflow-y-hidden` so it fills available space without expanding the parent
- Pages inside `main` control their own scroll behavior via `PageContainer` variant

## Preventing Double Scrollbars

The single most important rule: **only one element on the page should scroll**. If you see two scrollbars, something is wrong.

Rules:
1. The layout (`app/dashboard/layout.tsx`) already sets `overflow-hidden` on the root
2. `PageContainer` with `dashboard` or `prose` variant handles scrolling at the page level
3. If using the `app` variant, **you** must designate which inner element scrolls using `flex-1 min-h-0 overflow-y-auto`
4. Never put `overflow-y-auto` on two nested elements

## Flex Layout Rules

When placing components inside flex containers:

- **`min-h-0`** — Always add to any flex child that might scroll or contain a scrolling element. Without it, the flex child will expand beyond its bounds instead of clipping.
- **`flex-1`** — Use on the element that should grow to fill remaining space
- **`shrink-0`** — Use on headers, footers, and icons to prevent them from being squashed

```tsx
// Correct: header stays fixed, content scrolls
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14">Title</header>   {/* stays fixed */}
  <div className="flex-1 min-h-0 overflow-y-auto">   {/* scrolls */}
    <PageBody>...</PageBody>
  </div>
</div>

// Wrong: both header and content compete for space
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14">Title</header>
  <div className="h-full overflow-y-auto">   {/* will cause layout issues */}
    ...
  </div>
</div>
```

## Page Layout Usage

### Standard Dashboard Page

```tsx
import { PageContainer, PageBody } from "@/components/dashboard/page-container";

export default function TasksPage() {
  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <section>Section 1</section>
        <section>Section 2</section>
      </PageBody>
    </PageContainer>
  );
}
```

### Fixed-Height App Page

For chat or sandbox pages where the page is locked to viewport height with internal scrolling:

```tsx
import { PageContainer, PageBody } from "@/components/dashboard/page-container";

export default function ChatPage() {
  return (
    <PageContainer variant="app">
      <div className="shrink-0 h-14 border-b">Pinned Header</div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Content scrolls here */}
      </div>
      <div className="shrink-0 p-4 border-t">Pinned Footer/Input</div>
    </PageContainer>
  );
}
```

Note: `PageBody` is **not** used with the `app` variant because it applies `p-4 md:p-6 lg:p-10` padding that breaks the fixed-height layout.

## Handling User Input

Use `Zod` for validation and `react-hook-form` with the `zodResolver` for form logic.

## Component Sizing

- **Width**: Components should default to `w-full`. Let the `PageContainer` and parent flex containers control width — don't hardcode widths like `w-[400px]` inside components.
- **Height**: Avoid fixed heights like `h-[500px]`. Use `h-full` to fill a slot, or let content define the height.

## Component Placement Rules

### Client vs. Server Placement

Every component that uses React hooks (`useState`, `useEffect`, `useContext`, etc.) **must** have `'use client'` at the top of its file. When placing such a component:

1. If the page is a **server component** (`page.tsx` without `'use client'`), client components must appear as children inside `PageContainer`
2. The server page passes all data as props; the client component consumes it via hooks or context
3. Never call client hooks from server component files

```tsx
// ✅ CORRECT: ChatWidget is a client component, rendered inside the server page
// page.tsx (server component)
export default function ChatPage({ data }) {
  return (
    <PageContainer variant="app">
      <ChatWidget tokenUsage={data.context_tokens} />
    </PageContainer>
  )
}

// chat-widget.tsx (client component)
'use client'
export function ChatWidget({ tokenUsage }) {
  const { messages } = useChat()
  // ...
}
```

### Inside the Chat Context Tree

For chat-specific components that need access to `useChat()`, render them as children of `ChatProvider`. For example, a `TokenBar` that needs `tokenUsage` from context should be placed inside `ChatWidget` (which calls `useChat()`), not in the server page.

See [Frontend Pages](frontend-pages.md) for the full "Server vs. Client Components" and "PageContainer is the Root" rules.
