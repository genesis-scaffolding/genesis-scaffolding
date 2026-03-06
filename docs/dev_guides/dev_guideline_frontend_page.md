# Design Guideline: Layout, Sizing, and Scroll Management

This document defines how we handle page structure, scrolling, and component sizing to ensure a bug-free, consistent GUI.

Most of these design principles are captured in two helper components `PageContainer` and `PageBody`.

See the Quick Guide section below for process of how to use these helper components to quickly write a new page.

## Main Design Principle
To prevent the "double scrollbar" bug and ensure the UI never "explodes" when content is long, the root levels are strictly constrained to the viewport.

*   **Rule:** The browser window itself should **never** scroll.
*   **Implementation (`app/layout.tsx`)**: `body` must be `h-[100dvh] overflow-hidden`.
*   **Implementation (`app/dashboard/layout.tsx`)**: The `SidebarProvider` and `main` tags must enforce height limits.
    ```tsx
    // Dashboard Layout Structure
    <SidebarProvider className="h-[100dvh] overflow-hidden flex">
       <Sidebar />
       <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <header className="shrink-0 h-14" />
          <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
             {children}
          </main>
       </div>
    </SidebarProvider>
    ```

---


## Details about types of pages

### Archetype A & B: Standard Scrolling (`dashboard` | `prose`)
The page itself handles the scrollbar.
*   **Max-Width (`dashboard`)**: `max-w-[1600px]`
*   **Max-Width (`prose`)**: `max-w-5xl`
*   **Padding**: Handled by `PageBody`.

### Archetype C: Fixed "App" UI (`app`)
The page is locked to the screen height. Use this for Chat or Tools.
*   **Rule:** You must manually define which part scrolls using `flex-1 min-h-0 overflow-y-auto`.
```tsx
<PageContainer variant="app">
  <div className="shrink-0 h-14 border-b">Pinned Header</div>
  <div className="flex-1 min-h-0 overflow-y-auto">
    <PageBody> {/* Content scrolls here */} </PageBody>
  </div>
  <div className="shrink-0 p-4 border-t">Pinned Footer/Input</div>
</PageContainer>
```

---

## Component Sizing & The "Flex-Fix"

To keep the layout stable, components (cards, buttons, widgets) must follow these rules:

1.  **Widths**: Components should default to `w-full`. Do not hardcode widths like `w-[400px]` inside a component; let the Page control the width.
2.  **Heights**: Avoid fixed heights (e.g., `h-[500px]`). Use `h-full` to fill a slot or let content define the height.
3.  **The Magic Words**:
    *   **`min-h-0` / `min-w-0`**: **Mandatory** on any flex-child that contains a scrolling element. This prevents the child from expanding its parent.
    *   **`flex-1`**: Use to make a component grow to fill the available remaining space.
    *   **`shrink-0`**: Use on headers, footers, or icons to ensure they are never "squashed" by scrolling content.

---

### Implementation Reference: `page-container.tsx`

```tsx
// components/dashboard/page-container.tsx
export function PageContainer({ variant = "dashboard", children, className }) {
  const styles = {
    prose: "max-w-5xl mx-auto p-4 md:p-10 overflow-y-auto",
    dashboard: "max-w-[1600px] mx-auto overflow-y-auto",
    app: "max-w-none p-0 overflow-hidden flex flex-col",
  };
  return (
    <div className={cn("h-full w-full min-h-0", styles[variant], className)}>
      {children}
    </div>
  );
}

export function PageBody({ children, className }) {
  return (
    <div className={cn("flex flex-col gap-6 p-4 md:p-6", className)}>
      {children}
    </div>
  );
}
```

---

## Visual Checklist for PR Reviews

*   [ ] Does the page use `PageContainer`?
*   [ ] Is there more than one vertical scrollbar on the screen? (There should only be one).
*   [ ] Do headers stay pinned when scrolling?
*   [ ] Is `min-h-0` present on flex-parents of scrolling areas?
*   [ ] On mobile, is there at least `p-4` padding? (Handled automatically by `PageBody`).

---


## Quick Guide: Creating a New Page

When creating a `page.tsx`, follow these steps to ensure consistent padding and scrolling.

### Step 1: Choose your Archetype
Wrap your entire page content in a `<PageContainer variant="...">`.

| Variant | Best For | Behavior |
| :--- | :--- | :--- |
| **`dashboard`** | Grids, Tables, Overview | Standard padding, page-level scroll. |
| **`prose`** | Settings, Forms, Articles | Narrow width (readable), page-level scroll. |
| **`app`** | Chat, Sandbox, Canvas | No padding, **Fixed page** (Internal scroll only). |

### Step 2: Use `PageBody` for Content Spacing
For `dashboard` and `prose` variants, use `<PageBody>` to automatically apply standard padding (`p-6`) and vertical spacing (`gap-6`).

```tsx
// Standard Dashboard Page Template
import { PageContainer, PageBody } from "@/components/dashboard/page-container";

export default function MyPage() {
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

IMPORTANT: Do not use `PageBody` directly underneath the `PageContainer` if you are making an `app` page. The `PageBody` would break fixed page design and break the scrolling behaviour of internal components.

---
