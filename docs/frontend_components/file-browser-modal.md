# FileBrowserModal

## Overview

A controlled dialog that lets users browse files in their sandbox or upload new ones. It is used by workflow forms and job parameters to let users select a file as a workflow input. The modal has two tabs: Browse (search and select) and Upload (drop a new file).

## Subcomponent: FileBrowserModal

### Component Tree

```
FileBrowserModal (Dialog wrapper)
├── <DialogTrigger>  (rendered trigger prop, or default "Browse Sandbox" button)
└── <DialogContent>
      ├── <DialogHeader> — "Sandbox File Picker" title
      └── <Tabs> (Browse Files / Upload New)
          ├── <TabsContent value="browse">
          │     ├── <Input> (search filter)
          │     └── <ScrollArea> with file list
          │          └── <file button> per file (highlighted if currentValue)
          └── <TabsContent value="upload">
                └── <drop zone>
                      ├── <Input type="file"> (hidden, triggered by label button)
                      └── <label> Select File from Computer
```

### Props

| Prop | Type | Description |
|---|---|---|
| `onSelect` | `(file: SandboxFile) => void` | Callback invoked with the selected file object when user confirms a selection |
| `currentValue` | `string` \| `undefined` | The currently selected file path (highlights the matching file in the list) |
| `trigger` | `React.ReactNode` \| `undefined` | Custom trigger element. Defaults to a "Browse Sandbox" button if not provided |

**Usage examples:**

```tsx
// Default trigger button
<FileBrowserModal
  onSelect={(file) => setFormValue("file_path", file.relative_path)}
  currentValue={formValues.file_path}
/>

// Custom trigger — useful when embedding in a form field
<FileBrowserModal
  onSelect={handleFileSelect}
  trigger={
    <Button variant="secondary" size="sm">
      <FolderOpen className="h-4 w-4 mr-2" />
      Choose File
    </Button>
  }
  currentValue={selectedPath}
/>
```

The `onSelect` callback receives the full `SandboxFile` object (with `relative_path`, `name`, `size`, `mime_type`, etc.), not just the path string. Use the property needed for the form value.

### Internal State

| State | Type | Purpose |
|---|---|---|
| `files` | `SandboxFile[]` | List of files fetched from the server, filtered to allowed extensions |
| `loading` | `boolean` | True while fetching the file list |
| `uploading` | `boolean` | True while a file upload is in progress |
| `search` | `string` | Search filter string (substring match on filename) |
| `open` | `boolean` | Dialog open/close state |

### Internal Operations

**Fetch on Open**

A `useEffect` watches `open`. When the dialog opens, `fetchFiles()` runs:

```typescript
useEffect(() => {
  if (open) fetchFiles();
}, [open]);

async function fetchFiles() {
  const data = await getFilesAction();
  // Filter to only show files the backend and agent tools support
  const filtered = data.filter(f =>
    ALLOWED_EXTENSIONS.some(ext => f.name.toLowerCase().endsWith(ext))
  );
  setFiles(filtered);
}
```

Files are filtered to `.pdf`, `.txt`, `.md`, `.mdx` — matching what the sandbox filesystem and agent tools can handle.

**File Selection**

When a file button is clicked:

```typescript
onClick={() => { onSelect(file); setOpen(false); }}
```

The `onSelect` callback is invoked first with the file object, then the dialog closes. The parent component handles storing the value.

**Current Value Highlighting**

The `currentValue` prop compares against `file.relative_path`:

```typescript
currentValue === file.relative_path
  ? 'border-primary bg-primary/5'  // highlighted
  : ''                              // default
```

A checkmark icon is also shown on the matching file row.

**Upload with Immediate Selection**

The upload tab does not just upload — it immediately selects the file:

```typescript
async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  const newFile = await uploadFileAction(formData);
  onSelect(newFile);   // Immediately select the uploaded file
  setOpen(false);      // Close dialog
}
```

This skips the need to browse for a file just uploaded.

**Search Filter**

Search is applied client-side after the list loads:

```typescript
const filteredFiles = files.filter(f =>
  f.name.toLowerCase().includes(search.toLowerCase())
);
```

Simple substring match. The search is cleared when the dialog closes.

### Key Files

- `components/dashboard/file-browser-modal.tsx` — main component
- `app/actions/sandbox.ts` — `getFilesAction`, `uploadFileAction`
- `types/sandbox.ts` — `SandboxFile` type, `ALLOWED_EXTENSIONS`