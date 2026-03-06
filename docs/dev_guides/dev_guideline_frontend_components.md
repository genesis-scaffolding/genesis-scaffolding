# Frontend Contribution Guide: Supporting New Backend Entities

This guide explains how to integrate new backend entities (e.g., a `news` feature) into the frontend. It assumes the backend storage logic and FastAPI endpoints are already implemented.

## Frontend Overview

The frontend is a **Next.js** project located in the `myproject-frontend` monorepo.

### Tech Stack
- **Framework:** React (App Router)
- **UI Components:** Shadcn UI
- **Icons:** Lucide-react
- **Styling:** Tailwind CSS / PostCSS

### Data Flow
The frontend communicates with the FastAPI backend via two methods:
1.  **Server Actions:** Located in `app/actions/`. These fetch data from the FastAPI backend and stream it to the browser.
2.  **API Proxy:** Defined at `app/api/[...proxy]/route.ts`. This transparently proxies browser requests through Next.js to the FastAPI backend so the browser never interacts with the backend directly.

### Key Directories
| Path | Description |
| :--- | :--- |
| `app/actions/` | Server actions for data fetching |
| `app/dashboard/` | Application pages and routes |
| `components/dashboard/` | Reusable dashboard components |
| `types/` | TypeScript interface definitions |
| `lib/` | Shared utility functions (e.g., `api-client`) |
| `app/globals.css` | Global Tailwind configurations |

---

## Implementation Process

### 1. Information Gathering
Review the backend's **Pydantic schemas** to understand the data structures. Check the **FastAPI endpoints** to identify supported logic, such as filtering, sorting, or pagination.

### 2. Define Type Definitions
Define the entity types in the `types/` directory to ensure consistency across the application.

```tsx
// types/sandbox.ts
export interface SandboxFile {
  id: number;
  filename: string;
  size: number;
  created_at: string;
}

export const ALLOWED_EXTENSIONS = ['.pdf', '.txt'];
```

### 3. Develop Server Actions
Create actions in `app/actions/` to interact with FastAPI. Use the `apiFetch` utility to handle authentication and base URLs. Use `revalidatePath` to refresh the cache after mutations.

```tsx
'use server'
import { apiFetch } from "@/lib/api-client";
import { revalidatePath } from "next/cache";

export async function getAgentsAction() {
  const res = await apiFetch(`/agents/`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function createAgentAction(data: any) {
  const res = await apiFetch(`/agents/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/agents');
  return res.json();
}
```

### 4. Develop UI Components
Build your components in `components/dashboard/` using Shadcn and Lucide icons.

#### CSS & Scrolling Conventions
Components are often placed inside `flex` containers.
- **Page-level scrolling:** If the parent page handles scrolling, no extra CSS is needed.
- **Internal scrolling:** If the page is fixed-height (e.g., a chat app), use `min-h-0 overflow-y-auto` on the container intended to scroll.

#### Handling User Input
Use `Zod` for validation and `react-hook-form` with the `zodResolver` for form logic.

**Example: Scrollable List**
```tsx
export const MessageList = ({ messages }: { messages: any[] }) => {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto w-full">
      <div className="py-4 space-y-6">
        {messages.map((msg, i) => <MessageBubble key={i} message={msg} />)}
      </div>
    </div>
  );
};
```

---

## 5. Build Pages
Follow standard RESTful routing when creating pages under `app/dashboard/[collection]/`:
- `page.tsx`: List/Grid view.
- `create/page.tsx`: Creation form.
- `[id]/page.tsx`: Detail view.
- `[id]/edit/page.tsx`: Update form.

### Page Layouts
Wrap your page content in the `<PageContainer>` component to maintain system-wide styling.

| Variant | Use Case | Behavior |
| :--- | :--- | :--- |
| **`dashboard`** | Tables, Grids | Standard padding, page-level scroll. |
| **`prose`** | Forms, Settings | Narrow width, page-level scroll. |
| **`app`** | Chat, Canvas | No padding, fixed-height (internal scroll only). |

**Standard Usage:**
```tsx
import { PageContainer, PageBody } from "@/components/dashboard/page-container";

export default function MyPage() {
  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <header>Title</header>
        <section>Content</section>
      </PageBody>
    </PageContainer>
  );
}
```
*Note: Do not use `PageBody` inside an `app` variant, as it will break the fixed-height internal scrolling.*
