# QuickAddTask

## Overview

A smart input field that parses natural language text to extract task properties (title, project, dates) before submitting. It supports typing `#project` for project assignment, and date/time patterns like `due Monday` or `at 3pm` for deadline and scheduling. A suggestion popup appears when the user types after `#` to help select a project.

## Subcomponent: QuickAddTask

### Component Tree

```
QuickAddTask
├── <form>
│     ├── <Input> (pl-10 with icon left, badges right)
│     │     ├── <Plus icon / Loader2> (left)
│     │     └── <floating badges> (right, shows parsed date/project)
│     └── (badges: hardDeadline=red, scheduledStart=purple,
│          assignedDate=blue, project=amber)
└── <suggestion popup> (above or below, z-50, only when showSuggestions)
      ├── "Matching Projects" header
      └── <project button> per filtered project
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `defaultProjectId` | `number` \| `undefined` | `undefined` | Pre-assign created tasks to this project |
| `showToast` | `boolean` | `false` | Show a success toast with an undo action after task creation |
| `popupDirection` | `"above"` \| `"below"` | `"below"` | Where the project suggestion popup appears |

**Usage examples:**

```tsx
// In FloatingActionMenu — no pre-assigned project
<QuickAddTask showToast={true} popupDirection="above" />

// On a project page — pre-assign tasks to the current project
<QuickAddTask defaultProjectId={project.id} showToast={true} />

// Without toast — used in forms where parent handles feedback
<QuickAddTask defaultProjectId={projectId} showToast={false} />
```

`showToast` is set to `true` when used standalone (in the floating menu). When embedded in a form, the parent form typically handles the feedback and `showToast` is `false`.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `inputValue` | `string` | Current input text |
| `loading` | `boolean` | True while `createTaskAction` is in progress |
| `projects` | `Project[]` | Loaded once on mount via `getProjectsAction` |
| `showSuggestions` | `boolean` | Whether the project suggestion popup is visible |
| `activeIndex` | `number` | Keyboard-navigated index in the suggestion list |

**Refs:**

| Ref | Type | Purpose |
|---|---|---|
| `inputRef` | `HTMLInputElement` | Used to refocus input after selecting a project |

### Internal Operations

**Parser (`lib/task-parser.ts`)**

The parser runs on every keystroke via `useMemo`. It does three things:

1. **Project matching** — scans the input for `#<project name>` and resolves it to a project ID

```typescript
const sortedProjects = [...projects].sort((a, b) => b.name.length - a.name.length);
for (const project of sortedProjects) {
  const projectTag = `#${project.name}`;
  if (title.toLowerCase().includes(projectTag.toLowerCase())) {
    projectId = project.id;
    title = title.replace(new RegExp(escapedName, 'gi'), "");
    break;
  }
}
```

Projects are matched longest-first so that `#Deployment` does not match a project named `#Deployment and CI/CD`.

2. **Date parsing with chrono-node** — parses natural language dates and determines intent from the preceding word

```typescript
const results = chrono.parse(title);
results.forEach((result) => {
  const textBefore = title.substring(0, result.index).trim().toLowerCase();

  if (textBefore.endsWith("due") || textBefore.endsWith("by")) {
    hardDeadline = dateValue.toISOString();
  } else if (textBefore.endsWith("at") || textBefore.endsWith("@")) {
    scheduledStart = dateValue.toISOString();
  } else {
    assignedDate = format(dateValue, "yyyy-MM-dd");
  }
  title = title.replace(result.text, "");
});
```

The intent detection uses the word before the date: `due`/`by` means deadline, `at`/`@` means appointment, otherwise general planning date.

3. **Output** — returns the parsed task object with title, projectId, assignedDate, hardDeadline, scheduledStart

**Parser input syntax:**

| Pattern | Example | Result |
|---|---|---|
| `#<project name>` | `#Deployment` | Assigns to matching project |
| `due <date>` | `due Monday` | Sets hard_deadline |
| `by <date>` | `by Friday` | Sets hard_deadline |
| `at <time>` | `at 3pm` | Sets scheduled_start |
| `@<date>` | `@tomorrow` | Sets scheduled_start |
| `<date>` (general) | `tomorrow` | Sets assigned_date |

**Suggestion Popup Detection**

```typescript
const handleInputChange = (e) => {
  const cursorPosition = e.target.selectionStart || 0;
  const words = val.substring(0, cursorPosition).split(/\s/);
  const lastWord = words[words.length - 1];

  if (lastWord.startsWith("#")) {
    setShowSuggestions(true);
    setActiveIndex(0);
  } else {
    setShowSuggestions(false);
  }
};
```

The popup is shown when the cursor is inside a word that starts with `#`. Typing or moving the cursor out of a `#`-prefixed word closes the popup.

**Suggestion Selection**

```typescript
const selectProject = (projectName: string) => {
  const lastHashIndex = inputValue.lastIndexOf("#");
  const prefix = inputValue.substring(0, lastHashIndex);
  setInputValue(`${prefix}#${projectName} `);  // Keep the # prefix for visual clarity
  setShowSuggestions(false);
  inputRef.current?.focus();
};
```

The `#` prefix is preserved in the input after selection. This is intentional — the `#` visual cue confirms which project is assigned.

**Keyboard Navigation**

```typescript
const handleKeyDown = (e) => {
  if (!showSuggestions || filteredProjects.length === 0) return;

  if (e.key === "ArrowDown") {
    e.preventDefault();
    setActiveIndex((prev) => (prev + 1) % filteredProjects.length);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    setActiveIndex((prev) => (prev - 1 + filteredProjects.length) % filteredProjects.length);
  } else if (e.key === "Enter" || e.key === "Tab") {
    const currentWord = inputValue.split("#").pop()?.toLowerCase() || "";
    const topMatch = filteredProjects[activeIndex].name.toLowerCase();
    if (currentWord !== topMatch) {
      e.preventDefault();
      selectProject(filteredProjects[activeIndex].name);
    } else {
      setShowSuggestions(false);  // Exact match — let Enter submit
    }
  } else if (e.key === "Escape") {
    setShowSuggestions(false);
  }
};
```

If the current input exactly matches the top suggestion, Enter/Tab submits the form. Otherwise, it selects the suggestion first.

**Submit Flow**

```typescript
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  if (showSuggestions) return;  // Prevent submission while picking a project
  if (!parsed.title || loading) return;

  const newTask = await createTaskAction({
    title: parsed.title,
    project_ids: activeProjectId ? [activeProjectId] : [],
    assigned_date: parsed.assignedDate,
    hard_deadline: parsed.hardDeadline,
    scheduled_start: parsed.scheduledStart,
    status: "todo",
  });

  setInputValue("");
  if (showToast) {
    toast.success("Task created", {
      action: { label: "Undo", onClick: () => deleteTaskAction(newTask.id) }
    });
  }
  router.refresh();
}
```

The `showSuggestions` check prevents accidental submission while navigating the popup. The success toast includes an undo action that deletes the created task.

**Floating Badges**

Parsed properties are displayed as colored badges inside the input field, on the right side:

```
[Due: Apr 20] [At: 3:00 PM] [#Deploy]
```

Each badge is a different color:
- **Red** — hard deadline (`bg-red-50 text-red-600`)
- **Purple** — scheduled start (`bg-purple-50 text-purple-600`)
- **Blue** — assigned date without deadline (`bg-blue-50 text-blue-600`)
- **Amber** — project assignment (`bg-amber-50 text-amber-700`)

The badges use `pointer-events-none` so they do not interfere with input interaction.

### Key Files

- `components/dashboard/tasks/quick-add-task.tsx` — main component
- `lib/task-parser.ts` — `parseTaskInput` function
- `app/actions/productivity.ts` — `createTaskAction`, `deleteTaskAction`, `getProjectsAction`