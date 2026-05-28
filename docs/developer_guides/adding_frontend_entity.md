# Adding a New Entity to the Frontend

This guide describes how to add frontend pages and components for a new backend entity. It assumes you are working with the frontend codebase provided by this scaffolding project.

Before starting, read these four documents carefully. They cover the structure and patterns that everything else depends on:
- [frontend_architecture.md](../frontend_architecture.md) — overall app structure, tech stack, communication pattern
- [frontend_data_flow.md](../frontend_data_flow.md) — how browser, Next.js, and FastAPI communicate
- [frontend_component_tree.md](../frontend_component_tree.md) — full component hierarchy and layout rules
- [frontend_layout_system.md](../frontend_layout_system.md) — CSS constraints, flex rules, PageContainer pattern

Also read the relevant component docs in [frontend_components/](../frontend_components/) for reusable components like DataTable and InlineEditForm.

## Prerequisites

Ensure the entity is accessible via the backend REST API before building the frontend. The guide assumes the entity has these endpoints:

- `GET /entity_name` — list with optional filters
- `POST /entity_name` — create
- `GET /entity_name/{id}` — get one
- `PATCH /entity_name/{id}` — partial update
- `DELETE /entity_name/{id}` — delete

See [adding_new_entity_to_backend.md](./adding_new_entity_to_backend.md.md) for how to add the backend entity first.

## Planning

### Pages

All new pages sit under `genesis-frontend/app/dashboard/`. The standard pages for an entity are:

| Path | Purpose |
|---|---|
| `app/dashboard/<entity_name>/page.tsx` | Collection view — list all items, provide links to create, view, or edit |
| `app/dashboard/<entity_name>/[id]/page.tsx` | Detail view — display a single item |
| `app/dashboard/<entity_name>/[id]/edit/page.tsx` | Edit view — form to update a single item |

In some cases, the edit page can serve as the detail page as well.

### Components

Place entity-specific components under `genesis-frontend/components/dashboard/<entity_name>/`.

Try to reuse existing components first. See [frontend_components/](../frontend_components/) for documentation on:
- `DataTable` — for rendering lists with sorting, filtering, and pagination
- `InlineEditForm` — for in-place text editing
- `MarkdownRenderer` — for rendering markdown content

If you need generic components like forms or cards, adapt the shared components already in the codebase. Otherwise, design new components as needed.

### Component design principles

- Components should not fetch data or mutate data directly. Data is fetched by the containing page and passed as props.
- Similarly, mutations are triggered by passing callback functions as props from the containing page.
- Avoid passing React components as props unless necessary. For example, if building a form button, prefer accepting a `label` prop rather than a whole `ReactNode` prop. This keeps the interface simpler and easier to reason about.

## Step-by-Step Implementation

### Step 1: Define Types

Create TypeScript types for the entity in `genesis-frontend/types/`. If a relevant file already exists, add the types there. Otherwise, create a new file `genesis-frontend/types/<entity_name>.ts`.

At minimum, define:
- `EntityName` — the full entity shape
- `EntityNameCreate` — fields required to create
- `EntityNameUpdate` — fields that can be updated (all optional)
- `EntityNameRead` — response shape returned by the API (usually same as `EntityName`)

```typescript
// types/<entity_name>.ts

export interface EntityName {
  id: number;
  name: string;
  status: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntityNameCreate {
  name: string;
  status?: string;
}

export interface EntityNameUpdate {
  name?: string;
  status?: string;
}
```

### Step 2: Create Server Actions

Create server actions in `genesis-frontend/app/actions/<entity_name>.ts` to call the backend API via the proxy route. This separates API communication from page logic.

```typescript
// app/actions/<entity_name>.ts
'use server'

import { apiFetch } from "@/lib/api-client";
import { EntityName, EntityNameCreate, EntityNameUpdate } from "@/types/<entity_name>";

export async function getEntitiesAction(): Promise<EntityName[]> {
  const res = await apiFetch(`/entity_name/`);
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}

export async function getEntityAction(id: number): Promise<EntityName> {
  const res = await apiFetch(`/entity_name/${id}`);
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
}

export async function createEntityAction(data: EntityNameCreate): Promise<EntityName> {
  const res = await apiFetch(`/entity_name/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create");
  return res.json();
}

export async function updateEntityAction(id: number, data: EntityNameUpdate): Promise<EntityName> {
  const res = await apiFetch(`/entity_name/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update");
  return res.json();
}

export async function deleteEntityAction(id: number): Promise<void> {
  const res = await apiFetch(`/entity_name/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete");
}
```

Import the actions in pages and call them to fetch data. Use `revalidatePath` to refresh page data after mutations.

### Step 3: Create Pages

Follow the frontend layout system to choose the correct PageContainer variant for each page. Use `variant="dashboard"` for collection pages and `variant="prose"` for forms and detail pages.

**Collection page** — `app/dashboard/<entity_name>/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import { getEntitiesAction } from "@/app/actions/<entity_name>";

export default async function EntityListPage() {
  const items = await getEntitiesAction();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <section>
          {/* Collection content — table, cards, or list */}
        </section>
      </PageBody>
    </PageContainer>
  );
}
```

**Detail page** — `app/dashboard/<entity_name>/[id]/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import { getEntityAction } from "@/app/actions/<entity_name>";
import { notFound } from "next/navigation";

export default async function EntityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await getEntityAction(parseInt(id)).catch(() => null);
  if (!item) notFound();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        {/* Detail content */}
      </PageBody>
    </PageContainer>
  );
}
```

**Edit page** — `app/dashboard/<entity_name>/[id]/edit/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import { getEntityAction } from "@/app/actions/<entity_name>";
import EntityEditForm from "@/components/dashboard/<entity_name>/edit-form";
import { notFound } from "next/navigation";

export default async function EntityEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await getEntityAction(parseInt(id)).catch(() => null);
  if (!item) notFound();

  return (
    <PageContainer variant="prose">
      <PageBody>
        <EntityEditForm item={item} />
      </PageBody>
    </PageContainer>
  );
}
```

### Step 4: Create Components

Create components under `genesis-frontend/components/dashboard/<entity_name>/`. Common components:

- `columns.tsx` — TanStack column definitions for DataTable
- `<entity-name>-table.tsx` — DataTable wired with columns and toolbar
- `edit-form.tsx` — form for creating or editing
- `detail-view.tsx` — display component for a single item

**DataTable columns** — `components/dashboard/<entity_name>/columns.tsx`:

```typescript
import { ColumnDef } from "@tanstack/react-table";
import { EntityName } from "@/types/<entity_name>";

export const entityColumns: ColumnDef<EntityName, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "created_at",
    header: "Created",
  },
];
```

**Entity table** — `components/dashboard/<entity_name>/<entity-name>-table.tsx`:

```tsx
'use client'

import { EntityName } from "@/types/<entity_name>";
import DataTable from "@/components/dashboard/shared/data-table/data-table";
import { entityColumns } from "./columns";

interface EntityTableProps {
  data: EntityName[];
}

export default function EntityTable({ data }: EntityTableProps) {
  return (
    <DataTable
      data={data}
      columns={entityColumns}
      getRowId={(row) => row.id.toString()}
    />
  );
}
```

**Edit form** — `components/dashboard/<entity_name>/edit-form.tsx`:

```tsx
'use client'

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { EntityName, EntityNameUpdate } from "@/types/<entity_name>";
import { updateEntityAction } from "@/app/actions/<entity_name>";
import { InlineEditForm } from "@/components/ui/inline-edit-form";

interface EntityEditFormProps {
  item: EntityName;
}

export default function EntityEditForm({ item }: EntityEditFormProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleUpdate = (field: string, value: string) => {
    startTransition(async () => {
      try {
        const data: EntityNameUpdate = { [field]: value };
        await updateEntityAction(item.id, data);
        toast.success("Updated");
        router.refresh();
      } catch {
        toast.error("Failed to update");
      }
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <InlineEditForm
        value={item.name}
        onConfirm={(value) => handleUpdate("name", value)}
        onCancel={() => {}}
        loading={isPending}
      />
      {/* more fields */}
    </div>
  );
}
```

### Step 5: Add Navigation Link

Add the new entity to the sidebar in `app/dashboard/layout.tsx`. Find the appropriate `navGroups` section and add a new item:

```typescript
{
  label: "Data",
  items: [
    // existing items
    {
      title: "Sources",
      url: "/dashboard/sources",
      icon: FileText,  // choose a Lucide icon
      tooltip: "Manage document sources"
    },
  ]
}
```

Import the icon from `lucide-react` at the top of the file.

## Files to Create

```
genesis-frontend/types/
    <entity_name>.ts           # TypeScript types

genesis-frontend/app/actions/
    <entity_name>.ts           # Server actions

genesis-frontend/app/dashboard/<entity_name>/
    page.tsx                   # Collection page
    [id]/
        page.tsx               # Detail page
        edit/
            page.tsx           # Edit page

genesis-frontend/components/dashboard/<entity_name>/
    columns.tsx                # DataTable column definitions
    <entity-name>-table.tsx    # Table component
    edit-form.tsx               # Edit form component
```

## Testing

After creating the files, run the dev server and verify:
1. The new pages appear in the sidebar and are accessible
2. Data is fetched and displayed correctly
3. Create, update, and delete operations work end-to-end
4. No layout issues (scroll, flex sizing) appear in the browser

---

## Example: Adding a Source Entity

This section demonstrates the process described above by adding frontend support for the Source entity created in [adding_new_entity_to_backend.md](./adding_new_entity_to_backend.md).

### Step 1: Types

Create `genesis-frontend/types/source.ts`:

```typescript
export type SourceType = "web" | "file" | "note";

export interface Source {
  id: number;
  name: string;
  url: string | null;
  source_type: SourceType;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceCreate {
  name: string;
  url?: string;
  source_type?: SourceType;
  description?: string;
}

export interface SourceUpdate {
  name?: string;
  url?: string;
  source_type?: SourceType;
  description?: string;
}
```

### Step 2: Server Actions

Create `genesis-frontend/app/actions/sources.ts`:

```typescript
'use server'

import { apiFetch } from "@/lib/api-client";
import { Source, SourceCreate, SourceUpdate } from "@/types/source";

export async function getSourcesAction(): Promise<Source[]> {
  const res = await apiFetch(`/sources/`);
  if (!res.ok) throw new Error("Failed to fetch sources");
  return res.json();
}

export async function getSourceAction(id: number): Promise<Source> {
  const res = await apiFetch(`/sources/${id}`);
  if (!res.ok) throw new Error("Failed to fetch source");
  return res.json();
}

export async function createSourceAction(data: SourceCreate): Promise<Source> {
  const res = await apiFetch(`/sources/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create source");
  return res.json();
}

export async function updateSourceAction(id: number, data: SourceUpdate): Promise<Source> {
  const res = await apiFetch(`/sources/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update source");
  return res.json();
}

export async function deleteSourceAction(id: number): Promise<void> {
  const res = await apiFetch(`/sources/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete source");
}
```

### Step 3: Pages

Create `genesis-frontend/app/dashboard/sources/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import SourceTable from "@/components/dashboard/sources/source-table";
import { getSourcesAction } from "@/app/actions/sources";

export default async function SourcesPage() {
  const sources = await getSourcesAction();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <SourceTable data={sources} />
      </PageBody>
    </PageContainer>
  );
}
```

Create `genesis-frontend/app/dashboard/sources/[id]/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import SourceDetail from "@/components/dashboard/sources/source-detail";
import { getSourceAction } from "@/app/actions/sources";
import { notFound } from "next/navigation";

export default async function SourceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const source = await getSourceAction(parseInt(id)).catch(() => null);
  if (!source) notFound();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <SourceDetail source={source} />
      </PageBody>
    </PageContainer>
  );
}
```

Create `genesis-frontend/app/dashboard/sources/[id]/edit/page.tsx`:

```tsx
import PageContainer from "@/components/dashboard/page-container";
import PageBody from "@/components/dashboard/page-body";
import SourceEditForm from "@/components/dashboard/sources/source-edit-form";
import { getSourceAction } from "@/app/actions/sources";
import { notFound } from "next/navigation";

export default async function SourceEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const source = await getSourceAction(parseInt(id)).catch(() => null);
  if (!source) notFound();

  return (
    <PageContainer variant="prose">
      <PageBody>
        <SourceEditForm source={source} />
      </PageBody>
    </PageContainer>
  );
}
```

### Step 4: Components

Create `genesis-frontend/components/dashboard/sources/columns.tsx`:

```typescript
import { ColumnDef } from "@tanstack/react-table";
import { Source } from "@/types/source";

export const sourceColumns: ColumnDef<Source, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "source_type",
    header: "Type",
  },
  {
    accessorKey: "url",
    header: "URL",
  },
  {
    accessorKey: "created_at",
    header: "Created",
  },
];
```

Create `genesis-frontend/components/dashboard/sources/source-table.tsx`:

```typescript
'use client'

import { Source } from "@/types/source";
import DataTable from "@/components/dashboard/shared/data-table/data-table";
import { sourceColumns } from "./columns";

interface SourceTableProps {
  data: Source[];
}

export default function SourceTable({ data }: SourceTableProps) {
  return (
    <DataTable
      data={data}
      columns={sourceColumns}
      getRowId={(row) => row.id.toString()}
    />
  );
}
```

Create `genesis-frontend/components/dashboard/sources/source-edit-form.tsx`:

```typescript
'use client'

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Source, SourceUpdate } from "@/types/source";
import { updateSourceAction } from "@/app/actions/sources";
import { InlineEditForm } from "@/components/ui/inline-edit-form";

interface SourceEditFormProps {
  source: Source;
}

export default function SourceEditForm({ source }: SourceEditFormProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleUpdate = (field: string, value: string) => {
    startTransition(async () => {
      try {
        const data: SourceUpdate = { [field]: value };
        await updateSourceAction(source.id, data);
        toast.success("Source updated");
        router.refresh();
      } catch {
        toast.error("Failed to update source");
      }
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Name</h3>
        <InlineEditForm
          value={source.name}
          onConfirm={(value) => handleUpdate("name", value)}
          onCancel={() => {}}
          loading={isPending}
        />
      </div>
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">URL</h3>
        <InlineEditForm
          value={source.url ?? ""}
          onConfirm={(value) => handleUpdate("url", value)}
          onCancel={() => {}}
          loading={isPending}
          multiline={false}
        />
      </div>
    </div>
  );
}
```

Create `genesis-frontend/components/dashboard/sources/source-detail.tsx`:

```typescript
'use client'

import { Source } from "@/types/source";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface SourceDetailProps {
  source: Source;
}

export default function SourceDetail({ source }: SourceDetailProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">{source.name}</h1>
        <p className="text-sm text-muted-foreground">{source.source_type}</p>
      </div>
      {source.url && (
        <div>
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
            {source.url}
          </a>
        </div>
      )}
      {source.description && <p className="text-sm">{source.description}</p>}
      <div className="flex gap-2">
        <Link href={`/dashboard/sources/${source.id}/edit`}>
          <Button variant="outline">Edit</Button>
        </Link>
      </div>
    </div>
  );
}
```

### Step 5: Navigation

In `app/dashboard/layout.tsx`, add a Sources item to the Data group:

```typescript
{
  label: "Data",
  items: [
    // existing items
    {
      title: "Sources",
      url: "/dashboard/sources",
      icon: FileText,
      tooltip: "Manage document sources"
    },
  ]
}
```

Import `FileText` from `lucide-react` at the top of the file.

### Files Created

```
genesis-frontend/types/
    source.ts

genesis-frontend/app/actions/
    sources.ts

genesis-frontend/app/dashboard/sources/
    page.tsx
    [id]/
        page.tsx
        edit/
            page.tsx

genesis-frontend/components/dashboard/sources/
    columns.tsx
    source-table.tsx
    source-edit-form.tsx
    source-detail.tsx
```
