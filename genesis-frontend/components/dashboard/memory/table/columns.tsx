"use client";

import { ColumnDef } from "@tanstack/react-table";
import { EventLog, TopicalMemory } from "@/types/memory";
import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import Link from "next/link";
import { FileText, Lightbulb, Edit2, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { MemoryDeleteDialog } from "@/components/dashboard/memory/memory-delete-dialog";

const dateSortingFn = (rowA: any, rowB: any, columnId: string) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  return new Date(a).getTime() - new Date(b).getTime();
};

export const getMemoryColumns = (): ColumnDef<EventLog | TopicalMemory>[] => [
  {
    accessorKey: "type",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Type" className="w-[80px]" />,
    sortingFn: (rowA, rowB) => {
      const typeA = rowA.original && "event_time" in rowA.original ? "event" : "topic";
      const typeB = rowB.original && "event_time" in rowB.original ? "event" : "topic";
      return typeA.localeCompare(typeB);
    },
    cell: ({ row }) => {
      const isEvent = row.original && "event_time" in row.original;
      return (
        <Badge variant="outline" className="capitalize text-[10px] px-1.5 py-0">
          {isEvent ? "Event" : "Topic"}
        </Badge>
      );
    },
  },
  {
    accessorKey: "subject",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Subject" />,
    cell: ({ row }) => {
      const original = row.original;
      const href = original && "event_time" in original
        ? `/dashboard/memory/${original.id}?type=event`
        : `/dashboard/memory/${original.id}?type=topic`;
      const Icon = original && "event_time" in original ? FileText : Lightbulb;
      return (
        <Link
          href={href}
          className="hover:underline font-medium text-primary flex items-center gap-2"
        >
          <Icon className="h-3 w-3 text-muted-foreground" />
          {original.subject || "Untitled"}
        </Link>
      );
    },
  },
  {
    accessorKey: "event_time",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Date" className="w-[120px]" />,
    sortingFn: dateSortingFn,
    cell: ({ row }) => {
      const original = row.original as EventLog;
      if (!original.event_time) return <span className="text-muted-foreground">-</span>;
      return (
        <span className="font-mono text-xs">
          {format(new Date(original.event_time), "yyyy-MM-dd")}
        </span>
      );
    },
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Created" className="w-[120px]" />,
    sortingFn: dateSortingFn,
    cell: ({ row }) => {
      const original = row.original;
      return (
        <span className="font-mono text-xs">
          {format(new Date(original.created_at), "yyyy-MM-dd")}
        </span>
      );
    },
  },
  {
    accessorKey: "tags",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Tags" />,
    cell: ({ row }) => {
      const tags = row.original.tags || [];
      if (tags.length === 0) return <span className="text-muted-foreground">-</span>;
      return (
        <div className="flex flex-wrap gap-1">
          {tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
              {tag}
            </Badge>
          ))}
          {tags.length > 3 && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              +{tags.length - 3}
            </Badge>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: "importance",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Imp" className="w-[60px]" />,
    cell: ({ row }) => {
      const importance = row.original.importance;
      return (
        <Badge variant={importance >= 4 ? "default" : "secondary"} className="text-[10px] px-1.5 py-0">
          {importance}
        </Badge>
      );
    },
  },
  {
    accessorKey: "source",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Source" className="w-[100px]" />,
    cell: ({ row }) => {
      const source = row.original.source;
      return (
        <span className="text-xs text-muted-foreground capitalize">
          {source.replace("_", " ")}
        </span>
      );
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const original = row.original;
      const isEvent = original && "event_time" in original;
      const type = isEvent ? "event" : "topic";
      const href = `/dashboard/memory/${original.id}/edit?type=${type}`;
      return (
        <div className="flex items-center gap-2">
          <MemoryDeleteDialog
            id={original.id}
            memoryType={type}
            subject={original.subject ?? undefined}
          >
            <button className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-destructive/10">
              <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
            </button>
          </MemoryDeleteDialog>
          <Link
            href={href}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Edit2 className="h-4 w-4 text-muted-foreground hover:text-primary" />
          </Link>
        </div>
      );
    },
  },
];
