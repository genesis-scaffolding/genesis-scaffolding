# Developer Guide: Data Table System

This guide explains how to use the project's **Data Table Engine** to build powerful, sortable, and filterable tables for any backend entity, with a specific focus on advanced sorting logic.

## Architecture Overview

The system uses a **Three-Layer Architecture** powered by `@tanstack/react-table`. This separates the complex table logic (sorting, selection, visibility) from the UI and the specific data being displayed.

### Directory Structure
| Path | Responsibility |
| :--- | :--- |
| `components/dashboard/shared/data-table/` | **Shared UI Layer:** Generic table engine, sortable headers, and column togglers. |
| `components/dashboard/[entity]/table/` | **Definition Layer:** Column definitions (`columns.tsx`) and specific filters (`toolbar.tsx`). |
| `components/dashboard/[entity]/[entity]-table.tsx` | **Orchestrator:** Connects the engine to the definitions, defines default sorting, and handles bulk logic. |

---

## 1. Sorting Fundamentals

### The `DataTableColumnHeader`
To make a column sortable, you must use the `DataTableColumnHeader` component in the column definition. This provides the UI for toggling between Ascending, Descending, and Clear.

```tsx
header: ({ column }) => <DataTableColumnHeader column={column} title="Due Date" />
```

### Initial & Multi-Field Sorting
The orchestrator component defines the `initialSorting` state. This allows you to stack multiple sort rules (e.g., sort by Status first, then by Date).

```tsx
const defaultSorting: SortingState = [
  { id: "status", desc: true },      // Primary sort
  { id: "hard_deadline", desc: false } // Secondary sort (tie-breaker)
];
```

---

## 2. Advanced Sorting Logic

By default, JavaScript sorts alphabetically or numerically. For production-grade tables, you often need to override this behavior.

### Pattern A: The "Nulls Last" Strategy
Standard sorting puts empty values (null/undefined) at the top of ascending lists. To force empty values to the bottom, use a custom `sortingFn`.

```tsx
const dateSortingWithNullsLast = (rowA: Row<any>, rowB: Row<any>, columnId: string) => {
  const a = rowA.getValue(columnId);
  const b = rowB.getValue(columnId);

  if (!a && !b) return 0;
  if (!a) return 1;  // Move nulls to the end
  if (!b) return -1; 
  
  return new Date(a).getTime() - new Date(b).getTime();
};
```

### Pattern B: Status Weight Sorting (Enums)
When sorting statuses (e.g., "In Progress" vs "Backlog"), alphabetical order is rarely useful. Use a weight map to define a logical "heat" or priority.

```tsx
const STATUS_WEIGHTS = { in_progress: 3, todo: 2, backlog: 1 };

const statusSortingFn = (rowA: Row<any>, rowB: Row<any>, columnId: string) => {
  const weightA = STATUS_WEIGHTS[rowA.getValue(columnId)] ?? 0;
  const weightB = STATUS_WEIGHTS[rowB.getValue(columnId)] ?? 0;
  return weightA - weightB; // Use desc: true in initialSorting to show highest weight first
};
```

---

## 3. Implementation Workflow (Example: `Task` Entity)

### Step 1: Define Columns with Custom Logic (`columns.tsx`)
```tsx
// components/dashboard/tasks/table/columns.tsx
export const getTaskColumns = (): ColumnDef<Task>[] => [
  {
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    sortingFn: statusSortingFn, // Apply custom weight sort
    cell: ({ row }) => <Badge>{row.getValue("status")}</Badge>,
  },
  {
    accessorKey: "hard_deadline",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Deadline" />,
    sortingFn: dateSortingWithNullsLast, // Apply "Nulls Last" sort
    cell: ({ row }) => <div>{row.getValue("hard_deadline") || "No Date"}</div>,
  }
];
```

### Step 2: Orchestrate and Set Default Sort (`task-table.tsx`)
```tsx
// components/dashboard/tasks/task-table.tsx
export function TaskTable({ tasks }: { tasks: Task[] }) {
  const columns = React.useMemo(() => getTaskColumns(), []);

  const defaultSorting = React.useMemo(() => [
    { id: "status", desc: true },        // Highest priority status first
    { id: "hard_deadline", desc: false } // Then soonest deadline
  ], []);

  return (
    <DataTable
      data={tasks}
      columns={columns}
      initialSorting={defaultSorting}
      getRowId={(row) => row.id.toString()}
      renderToolbar={(table) => <TaskTableToolbar table={table} />}
    />
  );
}
```

---

## 4. Selection and Bulk Actions
To handle bulk actions, use the `renderFloatingBar` prop. Access selected data using `table.getSelectedRowModel()`.

```tsx
renderFloatingBar={(table) => {
  const selectedRows = table.getFilteredSelectedRowModel().rows;
  const selectedIds = selectedRows.map(r => (r.original as any).id);
  
  if (selectedIds.length === 0) return null;
  
  return (
    <BulkActionBar 
      selectedIds={selectedIds} 
      onClear={() => table.resetRowSelection()} 
    />
  );
}}
```

---

## 5. Best Practices

1.  **Stable Accessors:** Use `accessorKey` for simple fields and `accessorFn` for nested data. Sorting and filtering rely on the raw value returned by these.
2.  **Memoization:** Always wrap `getColumns()` and `defaultSorting` in `useMemo`. This prevents the table from re-calculating logic on every state change (like typing in a search box).
3.  **Unique IDs:** Always provide `getRowId`. Without it, TanStack uses the array index, which causes selection to break when the user sorts the table.
4.  **Display vs. Data:** 
    - Use `accessorFn` to return a **sortable primitive** (string, number, date).
    - Use `cell` to return the **JSX/UI** (Badges, Links). Never try to sort based on a JSX element.
5.  **Multi-Sort:** Keep `enableMultiSort={true}` in the `DataTable` engine to allow users to `Shift + Click` multiple columns for complex manual sorting.
