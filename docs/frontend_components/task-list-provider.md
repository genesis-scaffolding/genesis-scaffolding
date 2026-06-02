# TaskListProvider

## Overview

A client-side state container that owns the optimistic task list for a page. It wraps `TaskTable` and `QuickAddTask` so they share a single source of truth for the row data and can dispatch optimistic updates (status changes, new task creation) that the table re-renders synchronously, before the server round-trip completes.

The provider is a thin wrapper around React's `useOptimistic` hook plus a typed reducer. It exports two contexts:

- `TaskListContext` — the optimistic list and the dispatch function
- `TaskListProviderActive` — a boolean flag indicating whether a provider is present in the tree

The second context lets consumers (notably `TaskTable`) distinguish "no provider" from "provider present with an empty list" without changing the public context shape. Components rendered outside any provider see a safe no-op default and fall back to props for reconciliation.

## Subcomponent: TaskListProvider

### Component Tree

```
TaskListProvider
└── TaskListProviderActive.Provider (value=true)
    └── TaskListContext.Provider (value={optimisticTasks, addOptimistic})
        └── {children}
```

The provider renders no DOM. It is purely a state owner.

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `tasks` | `Task[]` | required | The server-rendered task list. Used as the base state for the optimistic layer. |
| `projects` | `Project[]` | undefined | Accepted for API symmetry with `TaskTable`. Not used by the provider today. Reserved for future optimistic variants (e.g. project rename) that need to read project data from context. |
| `children` | `React.ReactNode` | required | The subtree that should see the optimistic list. Typically wraps `TaskTable` and `QuickAddTask` on the same page. |

**Usage example:**

```tsx
// app/dashboard/tasks/page.tsx
<TaskListProvider tasks={tasks} projects={projects}>
  <QuickAddTask />
  <TaskTable tasks={tasks} projects={projects} />
</TaskListProvider>
```

### Reducer Actions

```typescript
export type TaskOptimisticAction =
  | { type: "status"; taskId: number; status: Status }
  | { type: "create"; task: Task };
```

| Type | Payload | Behavior |
|---|---|---|
| `status` | `taskId`, `status` | Maps over the list and replaces the matching task's `status` field. Other fields are preserved. |
| `create` | `task` | Prepends the new task to the top of the list. De-dups by `id` defensively in case the same create is dispatched twice in rapid succession. |

Add new variants here when introducing new optimistic actions so the context API stays type-safe and the reducer remains exhaustive.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `optimisticTasks` | `Task[]` | The current optimistic task list. Components that render the row data should read this in preference to any prop they were passed, so the optimistic layer is the single source of truth. |

The `useOptimistic` hook holds the state internally. The provider wraps it in `React.useMemo` and exposes it via context.

### Dispatch Semantics

The `addOptimistic` function must be called from inside a `startTransition` boundary:

```typescript
startTransition(() => {
  addOptimistic({ type: "status", taskId, status: newStatus });
  // ...server action + router.refresh()
});
```

Inside a transition, React keeps the optimistic state visible while the async work runs. When the transition completes:

- If a new `tasks` prop arrives (the server re-rendered the page), `useOptimistic` reconciles the base state and the optimistic state is dropped.
- If no new prop arrives (e.g. the server action rejected), React reverts the optimistic state and the UI snaps back to the previous value.

If `addOptimistic` is called outside a transition, the dispatch is still applied but React cannot guarantee the revert behavior, so the optimistic update may stick around even when the server round-trip fails. Always wrap dispatches in `startTransition`.

### Default Context

```typescript
const defaultContextValue: TaskListContextValue = {
  optimisticTasks: [],
  addOptimistic: () => {},
};
```

Components rendered outside any provider (e.g. the floating `QuickAddTask` mounted by the dashboard layout, or isolated tests) see this default. The `addOptimistic` is a no-op, so dispatches are silently dropped and the page falls back to `router.refresh()` for reconciliation. The `TaskListProviderActive` flag is `false` in this case, so consumers that need to differentiate "no provider" from "provider with empty list" can branch on it.

## Integration Points

### TaskTable

`TaskTable` reads `optimisticTasks` from `TaskListContext` when `TaskListProviderActive` is `true`, otherwise it falls back to its `tasks` prop. This lets the same component be used in both modes — wrapped in a provider for the optimistic experience, or standalone for cases that do not need it (e.g. the dashboard home, isolated tests). See [task-table.md](./task-table.md).

### TaskStatusBadge

`TaskStatusBadge` is a cell of `TaskTable` so it can rely on the provider's `addOptimistic` to update the row. On click:

1. Close the popover immediately (synchronous UI feedback, outside the transition)
2. Inside `startTransition`, call `addOptimistic({ type: "status", taskId, status: newStatus })` to update the row in the same frame
3. Call `updateTaskAction` and `router.refresh()` in the background

### QuickAddTask

`QuickAddTask` is typically a sibling of `TaskTable` on the same page, so the provider is the only way to share optimistic state. On submit:

1. Clear the input and show the spinner immediately (synchronous UI feedback, outside the transition)
2. Call `createTaskAction` and await the new task
3. Inside `startTransition`, call `addOptimistic({ type: "create", task: newTask })` to prepend the row, then call `router.refresh()` to reconcile

If the surrounding tree has no provider, the dispatch is a no-op and only `router.refresh()` runs. See [quick-add-task.md](./quick-add-task.md).

## Key Files

- `components/dashboard/tasks/task-list-provider.tsx` — the provider, context, reducer, and default value
- `components/dashboard/tasks/task-table.tsx` — consumer (reads `optimisticTasks`)
- `components/dashboard/tasks/table/task-status-badge.tsx` — consumer (dispatches `status` actions)
- `components/dashboard/tasks/quick-add-task.tsx` — consumer (dispatches `create` actions)
- `app/dashboard/tasks/page.tsx` — wraps the provider around `QuickAddTask` and `TaskTable`
- `app/dashboard/projects/[id]/page.tsx` — wraps the provider around `TaskTable` and the floating `QuickAddTask` for the project page
