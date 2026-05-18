# FloatingActionMenu

## Overview

A fixed-position button that expands into a tray of quick-action icons. It appears on most dashboard pages to provide fast access to create tasks, journals, and open the quick chat panel. The tray has two modes: icon mode (default) and task input mode (expanded QuickAddTask).

## Subcomponent: FloatingActionMenu

### Component Tree

```
FloatingActionMenu (fixed position, z-50)
├── <trigger button>  (Zap icon, rotates 45deg when open, X when open)
└── <tray> (animated, appears when isOpen)
    ├── <icon tray mode>  (default when isOpen and activeWidget="none")
    │   ├── TrayIcon: Task
    │   ├── TrayIcon: Today's Journal
    │   ├── TrayIcon: Weekly Planning
    │   ├── TrayIcon: Misc Note
    │   └── TrayIcon: Chat
    └── <task input mode>  (when activeWidget="task")
        └── QuickAddTask
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `position` | `"bottom-right"` \| `"bottom-left"` \| `"top-right"` \| `"top-left"` | `"bottom-right"` | Screen corner placement |
| `defaultProjectId` | `number` \| `undefined` | `undefined` | Pre-assign created tasks to this project |

**Position classes:**

```typescript
const positionClasses: Record<Position, string> = {
  "bottom-right": "bottom-6 right-6 flex-col-reverse items-end",
  "bottom-left": "bottom-6 left-6 flex-col-reverse items-start",
  "top-right": "top-20 right-6 flex-col items-end",
  "top-left": "top-20 left-6 flex-col items-start",
};
```

`flex-col-reverse` is used on bottom positions so the tray icons stack upward from the main button.

**Usage examples:**

```tsx
// Default usage — button appears bottom-right
<FloatingActionMenu />

// On a project page, pre-assign tasks to the current project
<FloatingActionMenu defaultProjectId={project.id} />

// On a page where bottom-right is obstructed
<FloatingActionMenu position="bottom-left" />
```

`defaultProjectId` is passed directly to `QuickAddTask` when the task tray is opened.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `isOpen` | `boolean` | Controls whether the tray is visible |
| `activeWidget` | `"none"` \| `"task"` | Controls which expanded widget is shown inside the tray |
| `loading` | `string \| null` | Tracks which journal button is in a loading state (set to the button label while async call is in progress) |
| `quickChatOpen` | `boolean` | Controls whether QuickChatSheet is open (independent of tray state) |

### Internal Operations

**Tray Mode Switching**

When the user clicks the Task icon:
```typescript
setActiveWidget("task");  // tray switches to a wide task input panel
```

Closing (X button or successful task creation) resets:
```typescript
setActiveWidget("none");
setIsOpen(false);
```

**Journal Creation**

When a journal icon is clicked, `handleJournalRedirect` runs:

```typescript
const handleJournalRedirect = async (type: JournalType, dateObj: Date, label: string) => {
  setLoading(label);
  try {
    const entry = await findOrCreateJournalAction({
      entry_type: type,
      reference_date: format(dateObj, "yyyy-MM-dd"),
      title: `${type} - ${format(dateObj, "yyyy-MM-dd")}`
    });
    router.push(`/dashboard/journals/${entry.id}/edit`);
    setIsOpen(false);
  } finally {
    setLoading(null);
  }
};
```

`loading` is set to a string label (e.g., `"today"`, `"weekly"`) so the correct icon shows a spinner while the async call completes.

**QuickChatSheet**

The Chat icon does not open a tray widget. Instead it sets `quickChatOpen(true)`, which renders `QuickChatSheet` as a sibling component (not inside the tray):

```tsx
{/* Sibling, not nested */}
<QuickChatSheet open={quickChatOpen} onOpenChange={setQuickChatOpen} />
```

This means the chat sheet exists outside the tray's animation context.

### Key Files

- `components/dashboard/floating-action-menu.tsx` — main component, TrayIcon helper
- `components/dashboard/tasks/quick-add-task.tsx` — task input embedded in tray
- `components/dashboard/quick-chat-sheet.tsx` — chat sheet opened by Chat icon
- `app/actions/productivity.ts` — `findOrCreateJournalAction`