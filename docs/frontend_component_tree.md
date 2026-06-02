# Frontend Component Tree

This document maps the full component hierarchy from the HTML root down to the page level. Understanding this structure is essential for debugging CSS and layout issues.

## Root Level

```
<html lang="en">
  <body class="h-dvh overflow-hidden">
    <TooltipProvider>
      {children}
      <Toaster richColors closeButton />
    </TooltipProvider>
  </body>
</html>
```

Source: `app/layout.tsx`

Key points:
- `h-dvh` sets height to dynamic viewport height (mobile browser chrome safe)
- `overflow-hidden` prevents the browser window itself from scrolling
- `TooltipProvider` enables tooltips throughout the app
- `Toaster` is the global toast notification container

## Dashboard Layout Level

```
SidebarProvider (flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden)
├── Sidebar (collapsible="icon", border-r)
│   ├── SidebarHeader (logo link to /dashboard)
│   ├── SidebarContent
│   │   └── SidebarGroup (nav items per group)
│   │       └── SidebarMenuItem > SidebarMenuButton (Link)
│   └── SidebarFooter (user info card + logout)
└── <content wrapper div> (flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden)
    ├── <header> (shrink-0 h-14 border-b, contains SidebarTrigger + DynamicHeader)
    └── <main> (flex-1 min-h-0 overflow-y-hidden flex flex-col bg-slate-50/30)
        └── {children}  <-- This is where dashboard pages render
```

Source: `app/dashboard/layout.tsx`

Key points:
- `SidebarProvider` is a flex container. `Sidebar` takes its natural width. The content wrapper fills remaining space with `flex-1`.
- The content wrapper is a flex column. The header is `shrink-0` (fixed height). The main area is `flex-1` with `overflow-y-hidden`.
- `{children}` is the page content. Pages control their own scroll behavior via `PageContainer`.

## Page Level (Dashboard Pages)

Dashboard pages always wrap content in `PageContainer` and `PageBody`:

```
PageContainer (variant="dashboard")
├── <scrolling div> (overflow-y-auto w-full flex-1)
│   └── <centering div> (max-w-[1600px] mx-auto)
│       └── PageBody (flex flex-col gap-4 p-4 md:p-6 lg:p-10)
│           ├── <section> ... content sections ...
│           ├── <section> ... content sections ...
│           └── FloatingActionMenu (if hasFloatingActionMenu=true)
└── (no closing tag — PageContainer renders the closing div)
```

Source: `components/dashboard/page-container.tsx`

For pages with `variant="app"` (fixed-height layout like chat), the structure differs:

```
PageContainer (variant="app")
├── <fixed div> (overflow-hidden flex flex-col w-full flex-1 h-full)
│   └── <centering div> (max-w-none w-full h-full flex flex-col)
│       └── <page content>  (PageBody NOT used here)
│           ├── <pinned header>  (shrink-0, e.g., h-14)
│           ├── <scrollable middle>  (flex-1 min-h-0 overflow-y-auto)
│           └── <pinned footer>  (shrink-0, e.g., input bar)
```

## Full Tree: Root to Dashboard Home

```
<html>
  <body h-dvh overflow-hidden>
    <TooltipProvider>
      <div>
        <SidebarProvider flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden>
          <Sidebar collapsible="icon" border-r>
            <SidebarHeader>  <!-- genesis logo -->
            <SidebarContent>
              <SidebarGroup>  <!-- Dashboard link -->
              <SidebarGroup label="Productivity">
                <SidebarMenuItem>Projects</SidebarMenuItem>
                <SidebarMenuItem>Tasks</SidebarMenuItem>
                <SidebarMenuItem>Calendar</SidebarMenuItem>
                <SidebarMenuItem>Journal</SidebarMenuItem>
              </SidebarGroup>
              <SidebarGroup label="Interaction">
                <SidebarMenuItem>Agents</SidebarMenuItem>
                <SidebarMenuItem>Chat History</SidebarMenuItem>
                <SidebarMenuItem>Agent Memory</SidebarMenuItem>
              </SidebarGroup>
              <SidebarGroup label="Automation">
                <SidebarMenuItem>Workflows</SidebarMenuItem>
                <SidebarMenuItem>Schedules</SidebarMenuItem>
                <SidebarMenuItem>Activity</SidebarMenuItem>
              </SidebarGroup>
              <SidebarGroup label="Data">
                <SidebarMenuItem>Files</SidebarMenuItem>
              </SidebarGroup>
            </SidebarContent>
            <SidebarFooter>  <!-- user card + logout -->
          </Sidebar>

          <div flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden>
            <header shrink-0 h-14 border-b>
              <SidebarTrigger />
              <Divider h-4 w-[1px] />
              <DynamicHeader />  <!-- shows current page title -->
            </header>

            <main flex-1 min-h-0 overflow-y-hidden flex flex-col bg-slate-50/30>
              <!-- PAGE CONTENT STARTS HERE -->
              <PageContainer variant="dashboard">
                <div overflow-y-auto w-full flex-1>
                  <div max-w-[1600px] mx-auto>
                    <PageBody flex flex-col gap-4 p-4 md:p-6 lg:p-10>
                      <!-- Dashboard page content -->
                      <section grid grid-cols-1 md:grid-cols-3>  <!-- Metric cards -->
                      <section grid gap-8 grid-cols-1 lg:grid-cols-12>
                        <div lg:col-span-8>  <!-- Task list (no provider, reads from tasks prop) -->
                          <TaskTable variant="dashboard" tasks={agendaTasks} />
                        </div>
                        <div lg:col-span-4>  <!-- Agents + Workflows -->
                          <AgentCard />
                          <WorkflowCard />
                        </div>
                      </section>
                      <section>  <!-- Recent activity -->
                        <JobList />
                      </section>
                      <!-- FloatingActionMenu renders here (mounts its own provider-less QuickAddTask) -->
                    </PageBody>
                  </div>
                </div>
              </PageContainer>
              <!-- PAGE CONTENT ENDS HERE -->
            </main>
          </div>
        </SidebarProvider>
      </div>
      <Toaster />
    </TooltipProvider>
  </body>
</html>
```

## Chat Page Structure (app variant)

Chat pages use `variant="app"` instead of `variant="dashboard"`:

```
PageContainer (variant="app")
└── <fixed div> (overflow-hidden flex flex-col w-full flex-1)
    └── <centering div> (max-w-none w-full h-full flex flex-col)
        ├── <header> (shrink-0 h-14 border-b)
        │   └── ChatHeader
        ├── <message area> (flex-1 min-h-0 overflow-y-auto)
        │   └── <MessageList>
        │       └── <MessageBubble> per message
        └── <footer> (shrink-0 p-4 border-t)
            └── <ChatInput>
```

Key difference: The page itself has a pinned header and footer. The message area is `flex-1 min-h-0 overflow-y-auto` and scrolls independently. No `PageBody` is used.

## Task List Pages with TaskListProvider

Two pages wrap their `TaskTable` and `QuickAddTask` in a `TaskListProvider` so the row data, the status popover, and the quick-add input share the same optimistic state.

### `/dashboard/tasks/page.tsx` (global task list)

```
PageContainer (variant="dashboard")
└── PageBody
    └── <heading> (h1 + subtitle)
    └── TaskListProvider (tasks={tasks} projects={projects})
        ├── QuickAddTask
        └── TaskTable (tasks={tasks} projects={projects} variant="table")
            └── DataTable
                ├── <toolbar> TaskTableToolbar
                ├── <rows> per task (reads from optimisticTasks via context)
                └── <floating bar> BulkActionBar
```

### `/dashboard/projects/[id]/page.tsx` (project detail)

```
PageContainer (variant="dashboard")
└── PageBody
    ├── <header> (project name, status badge, description)
    ├── <metric cards> (progress, task count, open count, deadline)
    └── TaskListProvider (tasks={tasks} projects={projects})
        ├── <tasks section>
        │   └── TaskTable (variant="list" pagination floatingOffset={true})
        │       └── DataTable
        │           └── <floating bar> BulkActionBar (with bottom-24 offset)
        ├── <journal section>
        │   └── JournalTable
        └── <fixed bottom QuickAddTask> (defaultProjectId={project.id} popupDirection="above")
```

The project page keeps the `QuickAddTask` as a fixed-position bar at the bottom of the viewport. Fixed positioning is viewport-relative, so it works correctly even when the `QuickAddTask` lives inside the `TaskListProvider` subtree (it is not nested in the page's normal flow).

### Pages WITHOUT TaskListProvider

Not every page that shows a `TaskTable` is wrapped in a provider. The `TaskTable` component is dual-mode: it reads from the optimistic context when `TaskListProviderActive` is `true`, otherwise it falls back to the `tasks` prop.

- **Dashboard home** (`app/dashboard/page.tsx`) — renders a `TaskTable` directly with the filtered `agendaTasks` array as the prop. There is no shared optimistic state because the row actions would only affect the dashboard's filtered slice, not the underlying task list.
- **Floating `QuickAddTask` in `FloatingActionMenu`** — mounted by the dashboard layout, not by a page, so it has no shared table. It uses the provider-less code path (the dispatch is a no-op, `router.refresh()` reconciles).

See [frontend_components/task-list-provider.md](./frontend_components/task-list-provider.md) and [frontend_components/task-table.md](./frontend_components/task-table.md) for the optimistic state contract.

## Component Organization

```
components/
├── ui/                          # Shadcn base components
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   ├── sidebar.tsx              # Full sidebar system
│   ├── sheet.tsx
│   ├── tooltip.tsx
│   └── ...
├── dashboard/                   # Dashboard-specific components
│   ├── page-container.tsx       # PageContainer, PageBody
│   ├── floating-action-menu.tsx # FAB menu
│   ├── dynamic-header.tsx       # Shows current page title
│   ├── tasks/
│   │   ├── task-list-provider.tsx  # Optimistic state container
│   │   ├── task-table.tsx          # Table view (reads from provider or prop)
│   │   ├── quick-add-task.tsx      # Smart task input
│   │   ├── bulk-action-bar.tsx     # Floating bar for row selection
│   │   └── table/                  # Task table internals
│   │       ├── columns.tsx         # getTaskColumns factory
│   │       ├── toolbar.tsx         # TaskTableToolbar
│   │       └── task-status-badge.tsx  # Status popover (optimistic dispatch)
│   ├── jobs-table.tsx
│   ├── workflow-card.tsx
│   ├── agent-card.tsx
│   ├── start-chat-button.tsx    # Starts chat with agent
│   └── ... (more domain components)
├── auth/                         # Auth-specific components
│   ├── login-form.tsx
│   ├── register-form.tsx
│   └── logout-button.tsx
└── chat/                         # Chat-specific components
    ├── chat-context.tsx         # Chat session state
    ├── chat-input.tsx
    ├── message-bubble.tsx
    ├── message-list.tsx
    └── clipboard-drawer.tsx
```

## Why the Tree Matters

The most common layout bugs come from violating the scroll hierarchy:

1. **Double scrollbars** — when two nested elements both have `overflow-y-auto`. The fix is to ensure only one element scrolls at each level of the tree.

2. **Content cutoff** — when a flex child without `min-h-0` expands beyond its container. The fix is to add `min-h-0` to any flex child that contains a scrollable area.

3. **Sidebar collapsing breaks layout** — if adding components inside `main` without respecting `flex-1 min-h-0`, the content area may not shrink correctly when the sidebar expands.

Understanding which level of the tree manages scroll and which level manages flex growth is the key to resolving these issues.