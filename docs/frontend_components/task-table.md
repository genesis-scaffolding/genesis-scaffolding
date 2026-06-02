# TaskTable

## Overview

A reusable table component for the productivity task list. Built on top of the generic `DataTable` and reads its row data from the optimistic layer when wrapped in a `TaskListProvider`, otherwise from the `tasks` prop.

The component supports three visual variants:

- `table` — full table with all columns and pagination (default)
- `list` — condensed list view, used on the project detail page
- `dashboard` — agenda view, used on the dashboard home

The status column renders a `TaskStatusBadge` (a popover that lets the user change status optimistically). The toolbar renders column visibility toggles. The floating bar renders a `BulkActionBar` for row selection actions.

## Subcomponent: TaskTable

### Component Tree

```
TaskTable
└── DataTable
    ├── <toolbar slot>
    │     └── TaskTableToolbar (column visibility, future filters)
    ├── <Table>
    │     ├── <TableHeader>
    │     │     └── columns from getTaskColumns(variant)
    │     └── <TableBody>
    │          └── <TableRow> per task
    │               ├── <Checkbox> (select column)
    │               ├── <title cell> (link to task detail)
    │               ├── <project cell> (badge or Inbox)
    │               ├── <assigned_date cell>
    │               ├── <hard_deadline cell>
    │               ├── <scheduled_start cell>
    │               ├── <created_at cell>
    │               ├── <status cell> → TaskStatusBadge
    │               └── <actions cell> (edit link, hover-only)
    └── <floating bar slot>
          └── BulkActionBar (status, schedule, deadline, project, delete)
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `tasks` | `Task[]` | required | The server-rendered task list. Used directly when no `TaskListProvider` is present, or as the base for the optimistic layer. |
| `projects` | `Project[]` | required | Used by `getTaskColumns` to resolve the project name in the project column. |
| `variant` | `"table" \| "list" \| "dashboard"` | `"table"` | Visual variant. Controls which columns are visible and the default sort direction. |
| `floatingOffset` | `boolean` | `false` | Adds bottom margin to the floating `BulkActionBar` so it does not collide with a floating `QuickAddTask` on the same page. |
| `pagination` | `boolean` | derived | Show pagination. Defaults to `true` when `variant === "table"`. |

### Data Source

```typescript
const inProvider = React.useContext(TaskListProviderActive);
const { optimisticTasks } = React.useContext(TaskListContext);
const data = inProvider ? optimisticTasks : tasks;
```

When wrapped in a `TaskListProvider`, the provider's optimistic layer is the source of truth for the row data. When rendered standalone (e.g. the dashboard home, isolated tests, or any caller that has not wired up a provider), the `TaskListProviderActive` context is `false` and the component falls back to the `tasks` prop directly. This keeps the component usable in both modes without forcing every caller to opt in.

See [task-list-provider.md](./task-list-provider.md) for the optimistic state contract.

### Column Visibility

```typescript
const initialVisibility = {
  project: variant !== "list" && variant !== "dashboard",
  created_at: false,
  scheduled_start: false,
  assigned_date: variant !== "dashboard",
  hard_deadline: variant !== "dashboard",
};
```

The defaults keep the most relevant columns visible for each variant. Users can override visibility from the toolbar.

| Variant | Project | Assigned date | Hard deadline | Scheduled start | Created at |
|---|---|---|---|---|---|
| `table` | yes | yes | yes | yes | hidden by default |
| `list` | hidden | yes | yes | yes | hidden by default |
| `dashboard` | hidden | hidden | hidden | hidden | hidden by default |

### Default Sorting

```typescript
const defaultSorting: SortingState = [
  { id: "status", desc: true },           // To Do before Done
  { id: "hard_deadline", desc: false },   // Soonest first
  { id: "assigned_date", desc: variant === "dashboard" },
  { id: "scheduled_start", desc: variant === "dashboard" },
  { id: "created_at", desc: false },      // Oldest first
];
```

Multi-column sort is enabled. The status column sorts by `STATUS_WEIGHTS` (in_progress > todo > backlog > completed > canceled) so high-priority items float to the top.

### Columns

The columns are produced by `getTaskColumns(projects, variant)` in `components/dashboard/tasks/table/columns.tsx`. Key details:

- **Title cell** — links to `/dashboard/tasks/{id}`. Bolds the title for tasks scheduled for today. Turns red for tasks with a hard deadline this week that are not yet completed. Strikethrough for completed/canceled tasks in `list` variant.
- **Project cell** — resolves `project_ids[0]` against the `projects` prop. Falls back to "Inbox" when no project is linked. The badge links to the project page.
- **Status cell** — renders `TaskStatusBadge`, which dispatches the optimistic status update via the provider.

### Floating Bar

When the user selects rows, `BulkActionBar` renders fixed at the bottom of the viewport. The bar exposes status, schedule, deadline, project, and delete actions. The `floatingOffset` prop adds `bottom-24` to clear the floating `QuickAddTask` on the project detail page.

The bar is rendered through `DataTable.renderFloatingBar`. Selection state is read from the `DataTable` row model and passed in as `selectedIds` and `onClear`.

## Key Files

- `components/dashboard/tasks/task-table.tsx` — the component
- `components/dashboard/tasks/table/columns.tsx` — `getTaskColumns` factory
- `components/dashboard/tasks/table/toolbar.tsx` — `TaskTableToolbar`
- `components/dashboard/tasks/table/task-status-badge.tsx` — status cell (optimistic dispatch)
- `components/dashboard/tasks/bulk-action-bar.tsx` — floating bar for row selection
- `components/dashboard/shared/data-table/data-table.tsx` — generic table wrapper
