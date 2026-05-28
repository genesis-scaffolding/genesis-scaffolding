# CSS and Layout System

This document covers the layout constraints at each level of the component tree, the PageContainer/PageBody pattern, and the flex layout rules that keep the app stable.

## Constraints at Each Level

### Body (Root Layout)

```css
/* app/layout.tsx */
body h-dvh overflow-hidden
```

- The browser window itself never scrolls. All scrolling is contained within the component tree.
- `h-dvh` uses the dynamic viewport height (accounts for mobile browser chrome).

### Dashboard Main Content Area

```css
/* app/dashboard/layout.tsx */
main flex-1 min-h-0 overflow-y-hidden flex flex-col bg-slate-50/30
```

- The main area fills whatever space the sidebar does not use.
- `flex-1` makes it grow. `min-h-0` prevents it from expanding beyond the viewport.
- `overflow-y-hidden` prevents the main area itself from scrolling — pages control their own scroll behavior.

### PageContainer

```css
/* variant="dashboard" or "prose" */
overflow-y-auto w-full flex-1
```

- This is the element that scrolls for dashboard and prose pages.
- `overflow-y-auto` enables vertical scrolling when content exceeds viewport height.
- `w-full` and `flex-1` ensure it fills available space without expanding the parent.

### PageBody

```css
/* components/dashboard/page-container.tsx */
flex flex-col gap-4 p-4 md:p-6 lg:p-10
```

- Provides standard padding and vertical spacing between sections.
- **Not used** with `variant="app"` because the padding breaks fixed-height layouts.

## Three PageContainer Variants

| Variant | Max Width | Scroll Behavior | PageBody | Use Case |
|---|---|---|---|---|
| `dashboard` | `max-w-[1600px]` | Page-level scroll | Yes | Tables, grids, lists, dashboard home |
| `prose` | `max-w-5xl` | Page-level scroll | Yes | Forms, settings, detail pages |
| `app` | none | Fixed height, internal scroll only | **No** | Chat, sandbox file browser |

### Dashboard Variant

```tsx
<PageContainer variant="dashboard">
  <PageBody>
    <section>...</section>
    <section>...</section>
  </PageBody>
</PageContainer>
```

The page scrolls as a whole. Used for pages with tables, lists, or multiple content sections.

### App Variant (Fixed Height)

```tsx
<PageContainer variant="app">
  <div className="shrink-0 h-14 border-b">Pinned Header</div>
  <div className="flex-1 min-h-0 overflow-y-auto">
    {/* Content scrolls here */}
  </div>
  <div className="shrink-0 p-4 border-t">Pinned Footer</div>
</PageContainer>
```

The page is locked to viewport height. The page designer designates which inner element scrolls. `PageBody` is not used because its padding breaks this pattern.

### Prose Variant

```tsx
<PageContainer variant="prose">
  <PageBody>
    <form>...</form>
  </PageBody>
</PageContainer>
```

Used for forms and single-column content. Narrower max-width than dashboard.

## Flex Layout Rules

When building layouts inside dashboard pages, follow these rules to avoid scroll and sizing issues.

### Rule 1: Add min-h-0 to any flex child that might scroll

```tsx
// Correct
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14">Title</header>
  <div className="flex-1 min-h-0 overflow-y-auto">  {/* scrolls */}
    <PageBody>...</PageBody>
  </div>
</div>

// Wrong — content expands beyond bounds
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14">Title</header>
  <div className="flex-1 overflow-y-auto">  {/* missing min-h-0 */}
    ...
  </div>
</div>
```

Without `min-h-0`, a flex child with `overflow-y-auto` will expand beyond the parent instead of clipping at the boundary.

### Rule 2: Use shrink-0 on fixed elements

```tsx
// Header, footer, sidebar — never shrink
<header className="shrink-0 h-14 border-b">Pinned Header</header>
<footer className="shrink-0 p-4 border-t">Pinned Footer</footer>

// Icon-only elements
<div className="shrink-0">
  <SidebarIcon />
</div>
```

Without `shrink-0`, fixed-height elements may be squashed by flex growth.

### Rule 3: Only one element should scroll

The layout already sets `overflow-hidden` on the root body. Pages via `PageContainer` handle scrolling at one level. When designing inner layouts:

- Pick **one** element to scroll
- Do not put `overflow-y-auto` on two nested elements
- If you need a scrollable area inside a dashboard page, put it inside `PageBody` and accept the page-level scroll

### Rule 4: Use flex-1 on the element that should grow

```tsx
// Correct — main area grows to fill space
<main className="flex flex-1 flex-col min-h-0 overflow-hidden">
  {children}
</main>

// Wrong — main area takes only its content height
<main className="flex flex-col overflow-hidden">
  {children}
</main>
```

## Common Layout Bugs and Fixes

### Double scrollbars

**Cause**: Two nested elements both have `overflow-y-auto`.

**Fix**: Find the outer scrollable element. Remove `overflow-y-auto` from it, or move it to the correct level.

```tsx
// Before: two scrollable elements (double scrollbars)
<div className="overflow-y-auto">       {/* scrollbar 1 */}
  <div className="overflow-y-auto">     {/* scrollbar 2 */}
    <PageBody>...</PageBody>
  </div>
</div>

// After: only PageContainer scrolls
<div>
  <PageContainer>
    <PageBody>...</PageBody>
  </PageContainer>
</div>
```

### Content cutoff at bottom

**Cause**: A flex child with content exceeds container bounds.

**Fix**: Add `min-h-0` to the flex child that contains the overflowing content.

```tsx
// Before: content cutoff
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14" />
  <div className="flex-1 overflow-y-auto">  {/* missing min-h-0 */}
    {/* content overflows */}
  </div>
</div>

// After: content clips correctly
<div className="flex flex-col h-full">
  <header className="shrink-0 h-14" />
  <div className="flex-1 min-h-0 overflow-y-auto">  {/* min-h-0 added */}
    {/* content scrolls */}
  </div>
</div>
```

### Sidebar expand/collapse breaks layout

**Cause**: Adding content inside `main` without respecting the flex fill rules.

**Fix**: Ensure the page content area inside `main` uses `flex-1` to fill remaining space.

## Tailwind and Shadcn Styling

The app uses Tailwind CSS with Shadcn UI components.

- Base styles, CSS variables, and theme tokens are defined in `app/globals.css`
- Shadcn components use CSS variables that respond to `.dark` class on the root element
- Component classes are built by composing Tailwind utilities
- Custom components should use `cn()` from `lib/utils.ts` to merge class names safely

### Key CSS Variables

```css
/* Light theme (root level) */
--background: oklch(1 0 0)
--foreground: oklch(0.145 0 0)
--primary: oklch(0.205 0 0)
--border: oklch(0.922 0 0)

/* Dark theme (.dark class) */
--background: oklch(0.145 0 0)
--foreground: oklch(0.985 0 0)
--primary: oklch(0.922 0 0)
--border: oklch(1 0 0 / 10%)
```

The Shadcn sidebar and card components use these variables. Custom components should follow the same pattern.

## Utilities

### no-scrollbar

```css
/* app/globals.css */
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
```

Applied to elements where the scrollbar should be hidden but scrolling still works.

### cn() utility

```typescript
import { cn } from "@/lib/utils";

// Merges className safely, handling Tailwind class conflicts
<div className={cn("flex gap-2", className)} />
```