# Frontend Architecture

The genesis frontend is a Next.js web application that serves as the user-facing interface for the system. It communicates with the FastAPI backend exclusively through the Next.js process — browser code never calls FastAPI directly.

## Key Design Decisions

**No direct browser-to-FastAPI calls.** All communication goes through the Next.js server. Server Actions handle auth mutations, and an API proxy route forwards all other requests to FastAPI.

**JWT-based auth with httpOnly cookies.** Tokens are stored in cookies and automatically included on every request. Token refresh is handled transparently in both the Edge Middleware and the API client.

**Server Components as the default.** Pages and layouts are server components unless interactivity requires client components. This keeps the initial page load fast and reduces client-side JavaScript.

**Standardized page structure.** All dashboard pages use PageContainer and PageBody to enforce consistent layout, max-width, and scroll behavior.

**Optimistic updates through dedicated providers.** When two client components on the same page need to share optimistic state (e.g. a `TaskTable` row and a sibling `QuickAddTask`), the state is lifted into a dedicated client-side provider rather than buried inside one of the components. The provider owns the optimistic layer (typically `useOptimistic` plus a typed reducer), exposes it through context, and renders no DOM. Pages that need optimistic updates wrap the relevant components in the provider; pages that do not can use the same components as plain props-driven views. See [frontend_components/task-list-provider.md](./frontend_components/task-list-provider.md) for the canonical example.

## Documentation Structure

| Document | Contents |
|---|---|
| [frontend_data_flow.md](./frontend_data_flow.md) | How browser, Next.js, and FastAPI communicate. Server actions, API proxy, token injection, optimistic mutation flow. |
| [frontend_component_tree.md](./frontend_component_tree.md) | Full component hierarchy from HTML root to page-level components, including provider wrappings. |
| [frontend_layout_system.md](./frontend_layout_system.md) | CSS constraints, flex rules, PageContainer/PageBody pattern, preventing double scrollbars. |

## Codebase Structure

```
genesis-frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout (TooltipProvider, Toaster)
│   ├── globals.css        # Tailwind + Shadcn base styles
│   ├── actions/           # Server Actions (auth, API calls)
│   ├── api/[...proxy]/    # API proxy route
│   ├── dashboard/         # Dashboard pages and layout
│   ├── login/             # Login page
│   └── register/          # Registration page
├── components/
│   ├── ui/                # Shadcn base components
│   ├── dashboard/         # Shared and domain-specific components
│   ├── auth/              # LoginForm, LogoutButton
│   └── chat/              # ChatContext, MessageBubble, MessageList
├── lib/
│   ├── api-client.ts      # apiFetch with token injection and refresh
│   ├── auth.ts            # authenticateUser, refreshAccessToken
│   └── session.ts        # Cookie management
├── proxy.ts               # Edge Middleware (auth check, token refresh)
└── types/                 # TypeScript interfaces
```

## Tech Stack

- **Framework**: Next.js (App Router)
- **UI**: Shadcn UI components with Tailwind CSS
- **Icons**: Lucide React
- **Tables**: TanStack Table
- **Forms**: React Hook Form + Zod validation
- **Notifications**: Sonner toast

## Relevant Backend Docs

- [authentication.md](../authentication.md) — JWT token structure, login/logout flow, token refresh mechanism
- [architecture.md](./architecture.md) — System-level overview of all processes