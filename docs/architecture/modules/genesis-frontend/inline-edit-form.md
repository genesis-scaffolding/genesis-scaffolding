# Inline Edit Form

A reusable component for in-place editing of text content. Click to activate a textarea, then use keyboard shortcuts or buttons to confirm or cancel.

## Component: `InlineEditForm`

**Path:** `components/ui/inline-edit-form.tsx`

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `value` | `string` | — | The current content to edit |
| `onConfirm` | `(value: string) => Promise<void>` | — | Called with the new value when user confirms |
| `onCancel` | `() => void` | — | Called when user cancels (Esc, Cancel button, or blur) |
| `loading` | `boolean` | `false` | Disables input and shows spinner on Confirm button |
| `error` | `string \| null` | `null` | Shows red border + ring on input when set |
| `multiline` | `boolean` | `true` | `true` = textarea, `false` = single-line input |
| `minHeight` | `string` | `'200px'` | Minimum height of the textarea (e.g. `'400px'`, `'800px'`) |
| `className` | `string` | — | Additional CSS classes |

### Keyboard Behavior

**Multiline mode (default):**
- `Ctrl+Enter` or `Cmd+Enter` — confirms
- `Escape` — cancels
- `Shift+Enter` — inserts newline (does NOT confirm)

**Single-line mode (`multiline={false}`):**
- `Enter` — confirms
- `Escape` — cancels

### Visual Hints

The component always renders a hint below the textarea:
```
⌘+Enter to confirm | Esc to cancel
```

## Pattern: Building an Editor Wrapper

`InlineEditForm` is only the form — it does not manage display vs. edit state. The parent component owns that logic.

**Structure:**

```tsx
'use client'

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { InlineEditForm } from '@/components/ui/inline-edit-form';
import { updateAction } from '@/app/actions/...';

interface ContentEditorProps {
  id: string;
  initialValue: string;
}

export function ContentEditor({ id, initialValue }: ContentEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleConfirm = async (newValue: string) => {
    setLoading(true);
    try {
      await updateAction(id, { field: newValue });
      router.refresh();  // Re-fetch server data after mutation
      setIsEditing(false);
    } finally {
      setLoading(false);
    }
  };

  if (isEditing) {
    return (
      <InlineEditForm
        value={initialValue}
        onConfirm={handleConfirm}
        onCancel={() => setIsEditing(false)}
        loading={loading}
        minHeight="400px"  // Optional: adjust for content length
      />
    );
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="cursor-text hover:bg-muted/10 rounded-lg p-4 -m-4 transition-colors"
    >
      {/* display content */}
    </div>
  );
}
```

### Key decisions in the wrapper

1. **Server action inside `onConfirm`** — call the update action, which handles API communication and `revalidatePath`
2. **`router.refresh()` after success** — triggers Next.js to re-fetch server component data, so the page reflects the new value
3. **`setLoading(true)` in `onConfirm`, `finally` to false** — prevents double-submit and reflects async state to the user
4. **`onCancel` just sets `isEditing(false)`** — no server call needed, just exit edit mode

## Example: Journal Content Editor

**Path:** `components/dashboard/journals/journal-content-editor.tsx`

This component wraps the markdown prose of a journal entry with click-to-edit behavior.

```tsx
'use client'

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { InlineEditForm } from '@/components/ui/inline-edit-form';
import { updateJournalAction } from '@/app/actions/productivity';

interface JournalContentEditorProps {
  journalId: string;
  initialContent: string;
}

export function JournalContentEditor({ journalId, initialContent }: JournalContentEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleConfirm = async (newContent: string) => {
    setLoading(true);
    try {
      await updateJournalAction(journalId, { content: newContent });
      router.refresh();
      setIsEditing(false);
    } finally {
      setLoading(false);
    }
  };

  if (isEditing) {
    return (
      <InlineEditForm
        value={initialContent}
        onConfirm={handleConfirm}
        onCancel={() => setIsEditing(false)}
        loading={loading}
        multiline={true}
        minHeight="800px"
      />
    );
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="prose prose-slate dark:prose-invert max-w-none lg:prose-lg cursor-text hover:bg-muted/10 rounded-lg p-4 -m-4 transition-colors"
    >
      <ReactMarkdown>{initialContent}</ReactMarkdown>
    </div>
  );
}
```

### Usage in a page

```tsx
// app/dashboard/journals/[id]/page.tsx (Server Component)

import { JournalContentEditor } from '@/components/dashboard/journals/journal-content-editor';

export default async function JournalDetailPage({ params }) {
  const entry = await getJournalAction((await params).id);

  return (
    <PageContainer variant="prose">
      {/* ... header ... */}
      <JournalContentEditor
        journalId={entry.id.toString()}
        initialContent={entry.content}
      />
    </PageContainer>
  );
}
```

### Choosing `minHeight`

- `200px` — short fields, titles (default)
- `400px` — medium-length content like task descriptions
- `800px` — long prose, journal entries, documents

## Error Handling

When `error` prop is set, the input shows a red border:

```tsx
<InlineEditForm
  value={content}
  onConfirm={handleConfirm}
  onCancel={() => setIsEditing(false)}
  error={saveError}
/>
```

The edit mode stays open after an error so the user can retry. Your `onConfirm` callback should catch errors and pass the message:

```tsx
const handleConfirm = async (newValue: string) => {
  setLoading(true);
  try {
    await updateAction(id, { content: newValue });
    router.refresh();
    setIsEditing(false);
    setError(null);
  } catch (e) {
    setError('Failed to save. Please try again.');
  } finally {
    setLoading(false);
  }
};
```

## Using in Table Cells

For inline editing within a TanStack Table, the same pattern applies — the cell holds `isEditing` state and renders `InlineEditForm` when active:

```tsx
// In your table column definition
cell: ({ row }) => {
  const [isEditing, setIsEditing] = useState(false);

  if (isEditing) {
    return (
      <InlineEditForm
        value={row.original.name}
        onConfirm={async (name) => {
          await updateTaskAction(row.original.id, { name });
          router.refresh();
          setIsEditing(false);
        }}
        onCancel={() => setIsEditing(false)}
        multiline={false}
        className="w-full"
      />
    );
  }

  return (
    <span onClick={() => setIsEditing(true)} className="cursor-text hover:bg-muted/20 rounded px-1">
      {row.original.name}
    </span>
  );
}
```

The form expands to fill the cell width via `className="w-full"`.