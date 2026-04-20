"use client";

import { ColumnDef, Row } from "@tanstack/react-table";
import { JournalEntry, Project } from "@/types/productivity";
import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import Link from "next/link";
import { FileText, Edit2, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { JournalDeleteDialog } from "@/components/dashboard/journals/journal-delete-dialog";

/**
 * Custom sorting function that forces null/undefined values to the bottom
 * for date columns (reference_date).
 */
const dateSortingWithNullsLast = (rowA: Row<JournalEntry>, rowB: Row<JournalEntry>, columnId: string) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;

  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;

  const dateA = new Date(a).getTime();
  const dateB = new Date(b).getTime();

  return dateA - dateB;
};

export const getJournalColumns = (
  projects: Project[]
): ColumnDef<JournalEntry>[] => [
  {
    accessorKey: "reference_date",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Date" className="w-[120px]" />,
    sortingFn: dateSortingWithNullsLast,
    cell: ({ row }) => {
      const date = row.getValue("reference_date") as string;
      if (!date) return <span className="text-muted-foreground">-</span>;
      return (
        <span className="font-mono text-xs">
          {format(new Date(date), "yyyy-MM-dd")}
        </span>
      );
    },
  },
  {
    accessorKey: "title",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Title" />,
    cell: ({ row }) => {
      const entry = row.original;
      return (
        <Link
          href={`/dashboard/journals/${entry.id}`}
          className="hover:underline font-medium text-primary flex items-center gap-2"
        >
          <FileText className="h-3 w-3 text-muted-foreground" />
          {entry.title || "Untitled Entry"}
        </Link>
      );
    },
  },
  {
    accessorKey: "entry_type",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Type" className="w-[100px]" />,
    cell: ({ row }) => {
      const type = row.getValue("entry_type") as string;
      return (
        <Badge variant="outline" className="capitalize text-[10px] px-1.5 py-0">
          {type}
        </Badge>
      );
    },
  },
  {
    accessorKey: "project",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Project" className="w-[150px]" />,
    accessorFn: (row) => {
      const projectId = row.project_id;
      const project = projects.find((p) => p.id === projectId);
      return project?.name || null;
    },
    cell: ({ row }) => {
      const projectName = row.getValue("project") as string | null;
      if (!projectName) return <span className="text-muted-foreground">-</span>;
      return <span className="text-sm">{projectName}</span>;
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const entry = row.original;
      return (
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link href={`/dashboard/journals/${entry.id}/edit`}>
            <Edit2 className="h-4 w-4 text-muted-foreground hover:text-primary" />
          </Link>
          <JournalDeleteDialog journalId={entry.id.toString()} entryTitle={entry.title || undefined}>
            <button className="cursor-pointer">
              <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
            </button>
          </JournalDeleteDialog>
        </div>
      );
    },
  },
];
