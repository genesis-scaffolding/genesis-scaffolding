# Frontend Components Guide

This guide explains how to integrate new backend entities into the frontend UI and build reusable components.

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
| `components/ui/` | Reusable UI primitives (Shadcn + custom) |
| `types/` | TypeScript interface definitions |
| `lib/` | Shared utilities including `api-client.ts` |

## Component Sizing

- **Width**: Components should default to `w-full`. Let the `PageContainer` and parent flex containers control width — don't hardcode widths like `w-[400px]` inside components.
- **Height**: Avoid fixed heights like `h-[500px]`. Use `h-full` to fill a slot, or let content define the height.

## Component Placement Rules

Every component that uses React hooks (`useState`, `useEffect`, `useContext`, etc.) **must** have `'use client'` at the top of its file. Server pages pass data as props; client components consume it via hooks or context.

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

## Shared Types

Types used by more than one file should live in the shared types file, not defined inline. When a type is needed across layers (server actions, components, pages), define it once in `types/chat.ts` (or the appropriate domain types file) and import it everywhere.

Example: `TokenUsage` is used by `ChatContext`, `QuickChatSheet`, and `openQuickChatAction` — it belongs in `types/chat.ts`, not in any of those individual files.

## Radix UI Accessibility Requirements

Radix UI primitives require specific wrapper components for accessibility. When using `Sheet` or `Dialog` from the project's Radix UI components:

- **`SheetContent` requires `SheetTitle`** — Without it, screen readers report a missing accessible label. Always wrap the heading inside `SheetTitle`:

```tsx
// ✅ Correct — screen reader accessible
<SheetContent side="right">
  <div className="py-4 px-4">
    <SheetTitle className="text-lg font-bold">Quick Chat</SheetTitle>
  </div>
</SheetContent>

// ❌ Wrong — triggers screen reader warning
<SheetContent side="right">
  <div className="py-4 px-4">
    <h2 className="text-lg font-bold">Quick Chat</h2>   {/* no SheetTitle */}
  </div>
</SheetContent>
```

The same rule applies to `Dialog` — use `DialogTitle` from the Dialog primitive.

For more information, see [Radix UI Dialog documentation](https://radix-ui.com/primitives/docs/components/dialog).

## Related Documentation

Architecture references for specific components:

- [Chat UI](../architecture/modules/genesis-frontend/chat-ui-components.md) — ChatProvider, message list, SSE streaming, inline edit in chat
- [Page Layout System](../architecture/modules/genesis-frontend/page-layout-system.md) — PageContainer, PageBody, dashboard layout, scroll rules
- [Markdown Rendering](../architecture/modules/genesis-frontend/markdown-rendering.md) — MarkdownText component with LaTeX support
- [Inline Edit Form](../architecture/modules/genesis-frontend/inline-edit-form.md) — Reusable inline editing component pattern