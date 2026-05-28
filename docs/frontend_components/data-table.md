# DataTable

## Overview

A generic table wrapper around TanStack Table. DataTable manages sorting, column visibility, row selection, and optional pagination locally. It receives data and column definitions as props and renders the table. Every entity table in the dashboard (tasks, jobs, workflows, agents, etc.) is built on top of this component.

## Subcomponent: DataTable

### Component Tree

```
DataTable
├── <toolbar slot> (optional, rendered above the table)
│     └── renderToolbar(table) — passed by parent
├── <Table>
│     ├── <TableHeader>
│     │     └── <TableRow> per header group
│     │          └── <TableHead> per column (uses flexRender)
│     └── <TableBody>
│          └── <TableRow> per row
│               └── <TableCell> per visible cell
├── <pagination controls> (optional, shown when enablePagination=true)
└── <floating bar slot> (optional)
      └── renderFloatingBar(table) — passed by parent
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `columns` | `ColumnDef<TData, TValue>[]` | required | TanStack column definitions (returned by entity-specific column functions) |
| `data` | `TData[]` | required | Row data array (fetched and passed by parent) |
| `getRowId` | `(row: TData) => string` | undefined | Custom row ID function. Without this, TanStack uses array index |
| `initialSorting` | `SortingState` | `[]` | Default sort columns on load |
| `enableMultiSort` | `boolean` | `true` | Allow multi-column sorting |
| `initialColumnVisibility` | `VisibilityState` | `{}` | Which columns are visible by default |
| `enablePagination` | `boolean` | `false` | Show pagination controls |
| `manualPagination` | `boolean` | `false` | True for server-side pagination (parent controls page) |
| `pageCount` | `number` | `-1` | Total page count (required when `manualPagination=true`) |
| `paginationState` | `PaginationState` | undefined | Controlled pagination state `{ pageIndex, pageSize }` |
| `onPaginationChange` | `(pageIndex, pageSize) => void` | undefined | Callback when page changes (used with controlled pagination) |
| `renderToolbar` | `(table) => React.ReactNode` | undefined | Render function for filter/search bar above table |
| `renderFloatingBar` | `(table) => React.ReactNode` | undefined | Render function for bulk action bar below table |

**Usage examples:**

```tsx
// Simple (all client-side, DataTable manages state)
<DataTable data={tasks} columns={columns} />

// With toolbar and floating bar
<DataTable
  data={tasks}
  columns={columns}
  renderToolbar={(table) => <TaskTableToolbar table={table} />}
  renderFloatingBar={(table) => <BulkActionBar ... />}
/>

// Server-side pagination (parent controls state)
<DataTable
  data={tasks}
  columns={columns}
  enablePagination={true}
  manualPagination={true}
  pageCount={totalPages}
  paginationState={pagination}
  onPaginationChange={(pageIndex, pageSize) => setPagination({ pageIndex, pageSize })}
/>
```

**Passing callbacks via renderToolbar and renderFloatingBar:**

Both slots receive the `table` instance from TanStack. The parent can pass callbacks that read from the table:

```tsx
<DataTable
  data={tasks}
  columns={columns}
  renderFloatingBar={(table) => {
    const selectedRows = table.getFilteredSelectedRowModel().rows;
    const selectedIds = selectedRows.map(row => row.original.id);
    return <BulkActionBar selectedIds={selectedIds} onClear={() => table.resetRowSelection()} />;
  }}
/>
```

The `table` object has methods for reading selection (`getFilteredSelectedRowModel()`), filtering, sorting, and pagination state — allowing the parent to build interactive controls that operate on the table's data.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `sorting` | `SortingState` | Current sort columns and directions |
| `columnVisibility` | `VisibilityState` | Which columns are visible |
| `columnFilters` | `ColumnFiltersState` | Active column filters |
| `rowSelection` | `{}` | Map of selected row IDs |
| `internalPagination` | `PaginationState` | Page index and size (only used when pagination is not controlled) |

### Internal Operations

**Controlled vs. Uncontrolled Pagination**

DataTable supports both patterns. A flag `isControlled = paginationState !== undefined` determines which path:

```typescript
const pagination = paginationState ?? internalPagination;
const isControlled = paginationState !== undefined;

const handlePaginationChange = (updaterOrValue) => {
  const newPagination = typeof updaterOrValue === 'function'
    ? updaterOrValue(pagination)
    : updaterOrValue;

  if (isControlled && onPaginationChange) {
    onPaginationChange(newPagination.pageIndex, newPagination.pageSize);
  } else {
    setInternalPagination(newPagination);
  }
};
```

When controlled, pagination state lives in the parent (useful for server-side pagination). When uncontrolled, DataTable manages it internally.

**TanStack Table Integration**

```typescript
const table = useReactTable({
  data,
  columns,
  getRowId: getRowId ? (row) => getRowId(row) : undefined,
  state: { sorting, columnVisibility, rowSelection, columnFilters, pagination },
  enableRowSelection: true,
  enableMultiSort,
  onSortingChange: setSorting,
  onColumnVisibilityChange: setColumnVisibility,
  onRowSelectionChange: setRowSelection,
  onPaginationChange: handlePaginationChange,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
  manualPagination: manualPagination,
  ...(manualPagination && { pageCount }),
});
```

**Custom Column Sorting**

Some columns need custom sort logic. Pass `sortingFn` in the column definition:

```typescript
// Sort null/undefined dates to the bottom regardless of direction
const dateSortingWithNullsLast = (rowA, rowB, columnId) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  return new Date(a).getTime() - new Date(b).getTime();
};

// Sort by status priority weight
const statusSortingFn = (rowA, rowB, columnId) => {
  const weightA = STATUS_WEIGHTS[rowA.getValue(columnId) as Status] ?? 0;
  const weightB = STATUS_WEIGHTS[rowB.getValue(columnId) as Status] ?? 0;
  return weightA - weightB;
};
```

### Key Files

- `components/dashboard/shared/data-table/data-table.tsx` — main component
- `components/dashboard/shared/data-table/column-header.tsx` — sortable column header with dropdown
- `components/dashboard/tasks/table/columns.tsx` — task column definitions and custom sort functions
- `components/dashboard/tasks/task-table.tsx` — task table orchestrator (wires DataTable with task-specific config)
- `components/dashboard/tasks/table/toolbar.tsx` — TaskTableToolbar (used as renderToolbar)
- `components/dashboard/tasks/bulk-action-bar.tsx` — BulkActionBar (used as renderFloatingBar)