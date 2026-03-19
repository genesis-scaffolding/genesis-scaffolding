# Developer Guide: Data Table System

This guide explains how to use the project's **Data Table Engine** to build powerful, sortable, and filterable tables for any backend entity.

## Architecture Overview

The system uses a **Three-Layer Architecture** powered by `@tanstack/react-table`. This separates the complex table logic (sorting, selection, visibility) from the UI and the specific data being displayed.

### Directory Structure
| Path | Responsibility |
| :--- | :--- |
| `components/dashboard/shared/data-table/` | **Shared UI Layer:** Generic table engine, sortable headers, and column togglers. |
| `components/dashboard/[entity]/table/` | **Definition Layer:** Column definitions (`columns.tsx`) and specific filters (`toolbar.tsx`). |
| `components/dashboard/[entity]/[entity]-table.tsx` | **Orchestrator:** Connects the engine to the definitions and handles bulk action logic. |

---

## 1. The Core Components

### `DataTable` (The Engine)
Located at `components/dashboard/shared/data-table/data-table.tsx`. It is a generic component that accepts any data type (`TData`).

**Key Props:**
- `columns`: The column definitions.
- `data`: The array of objects from the API.
- `getRowId`: **Critical.** A function returning a unique string ID for each row. This ensures selection state survives re-sorting.
- `renderToolbar`: A render-prop function that receives the `table` instance to render search/filters.
- `renderFloatingBar`: A render-prop function for bulk action bars.

### `DataTableColumnHeader`
Use this inside your column definitions to enable sorting UI.
```tsx
header: ({ column }) => <DataTableColumnHeader column={column} title="My Column" />
```

---

## 2. Implementation Workflow (Example: `News` Entity)

### Step 1: Define Columns (`columns.tsx`)
Create a file to define how data maps to the table. Use `accessorFn` for complex data (like nested objects) to ensure sorting works correctly.

```tsx
// components/dashboard/news/table/columns.tsx
export const getNewsColumns = (): ColumnDef<News>[] => [
  {
    accessorKey: "title",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Headline" />,
    cell: ({ row }) => <div className="font-bold">{row.getValue("title")}</div>,
  },
  {
    id: "category",
    accessorFn: (row) => row.category.name, // Extract string for sorting/filtering
    header: "Category",
  }
];
```

### Step 2: Create the Toolbar (`toolbar.tsx`)
The toolbar allows users to search and toggle column visibility.

```tsx
// components/dashboard/news/table/toolbar.tsx
export function NewsTableToolbar({ table }: { table: Table<any> }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <Input
        placeholder="Search headlines..."
        value={(table.getColumn("title")?.getFilterValue() as string) ?? ""}
        onChange={(e) => table.getColumn("title")?.setFilterValue(e.target.value)}
        className="h-8 w-[250px]"
      />
      <DataTableViewOptions table={table} />
    </div>
  );
}
```

### Step 3: Orchestrate in the Main Table Component
Create the entry-point component that brings everything together.

```tsx
// components/dashboard/news/news-table.tsx
export function NewsTable({ news }: { news: News[] }) {
  const columns = React.useMemo(() => getNewsColumns(), []);

  return (
    <DataTable
      data={news}
      columns={columns}
      getRowId={(row) => row.id.toString()}
      renderToolbar={(table) => <NewsTableToolbar table={table} />}
    />
  );
}
```

---

## 3. Advanced Patterns

### Selection and Bulk Actions
To handle bulk actions, use the `renderFloatingBar` prop. Access selected data using `table.getSelectedRowModel()`.

```tsx
renderFloatingBar={(table) => {
  const selectedIds = table.getSelectedRowModel().rows.map(r => r.original.id);
  return <BulkActionBar selectedIds={selectedIds} onClear={() => table.resetRowSelection()} />;
}}
```

### Context-Aware Visibility (Variants)
You can hide columns by default based on where the table is used (e.g., hiding the "Project" column when already inside a project page).

1. Add a `variant` prop to your Orchestrator.
2. Define `initialColumnVisibility` logic.

```tsx
// inside news-table.tsx
const initialVisibility = {
  category: variant !== "category-view", // Hide category column in specific views
};

<DataTable ... initialColumnVisibility={initialVisibility} />
```

---

## 4. Full Code Example: "Project Table"
Below is a complete implementation for a `Project` list using the system.

### A. Column Definition (`columns.tsx`)
```tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Project } from "@/types/productivity";
import { DataTableColumnHeader } from "../../shared/data-table/column-header";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export const projectColumns: ColumnDef<Project>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Project Name" />,
    cell: ({ row }) => (
      <Link href={`/dashboard/projects/${row.original.id}`} className="font-bold hover:underline">
        {row.getValue("name")}
      </Link>
    ),
  },
  {
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <Badge variant="outline">{row.getValue("status")}</Badge>,
  },
];
```

### B. The Toolbar (`toolbar.tsx`)
```tsx
"use client";

import { Table } from "@tanstack/react-table";
import { Input } from "@/components/ui/input";
import { DataTableViewOptions } from "../../shared/data-table/view-options";

export function ProjectTableToolbar<TData>({ table }: { table: Table<TData> }) {
  return (
    <div className="flex items-center justify-between py-4">
      <Input
        placeholder="Filter projects..."
        value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
        onChange={(e) => table.getColumn("name")?.setFilterValue(e.target.value)}
        className="max-w-sm h-8"
      />
      <DataTableViewOptions table={table} />
    </div>
  );
}
```

### C. The Orchestrator (`project-table.tsx`)
```tsx
"use client";

import * as React from "react";
import { Project } from "@/types/productivity";
import { DataTable } from "../shared/data-table/data-table";
import { projectColumns } from "./table/columns";
import { ProjectTableToolbar } from "./table/toolbar";

export function ProjectTable({ projects }: { projects: Project[] }) {
  // UseMemo prevents column re-definitions on every render
  const columns = React.useMemo(() => projectColumns, []);

  return (
    <DataTable
      data={projects}
      columns={columns}
      getRowId={(row) => row.id.toString()}
      renderToolbar={(table) => <ProjectTableToolbar table={table} />}
    />
  );
}
```

---

## 5. Best Practices
1.  **Memoize Columns:** Always wrap `getColumns()` calls in `useMemo` to prevent the table from re-calculating on every render.
2.  **Stable IDs:** Always provide `getRowId`. Without it, row selection will "jump" to different items when the list is sorted.
3.  **Formatting Strategy:**
    - **`accessorFn`**: Use this to return a plain **string or number**. This is what the engine uses for **sorting and filtering**.
    - **`cell`**: Use this to return **JSX/React Components** (Links, Badges, Buttons). This is only for **display**.
4.  **Loading States:** Tables are usually rendered in Server Components. Use React `Suspense` in the `page.tsx` for loading states while the Server Action fetches data.
