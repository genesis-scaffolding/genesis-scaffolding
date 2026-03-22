"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Task, Project } from "@/types/productivity";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import Link from "next/link";
import { Calendar, Edit2 } from "lucide-react";
import { cn } from "@/lib/utils";

// This function returns columns based on whether we are in "table" or "list" mode
export const getTaskColumns = (
  projects: Project[],
  variant: "table" | "list" = "table"
): ColumnDef<Task>[] => [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
          className="translate-y-[2px]"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
          className="translate-y-[2px]"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "title",
      // Use min-w on the header to push the other columns to the right
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Task" className="min-w-[400px]" />
      ),
      cell: ({ row }) => {
        const isCompleted = row.original.status === "completed";
        return (
          <div className="flex flex-col py-1">
            <Link
              href={`/dashboard/tasks/${row.original.id}`}
              className={cn(
                "font-medium hover:underline text-primary leading-tight",
                variant === "list" && isCompleted && "line-through opacity-50 text-muted-foreground"
              )}
            >
              {row.getValue("title")}
            </Link>
            {row.original.assigned_date && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mt-1">
                Scheduled: {row.original.assigned_date}
              </span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "project",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Project" />,
      accessorFn: (row) => {
        const projectId = row.project_ids?.[0];
        const project = projects.find((p) => p.id === projectId);
        return project?.name || "Inbox";
      },
      cell: ({ row }) => {
        const projectName = row.getValue("project") as string;
        const projectId = row.original.project_ids?.[0]; // Access the actual ID from the Task object

        // If it's the Inbox (no project), just show the text
        if (projectName === "Inbox" || !projectId) {
          return <span className="text-muted-foreground text-xs italic">Inbox</span>;
        }

        return (
          <Link href={`/dashboard/projects/${projectId}`}>
            <Badge
              variant="secondary"
              className="font-normal whitespace-nowrap hover:bg-secondary/80 transition-colors cursor-pointer"
            >
              {projectName}
            </Badge>
          </Link>
        );
      },
    },
    {
      accessorKey: "assigned_date",
      // Set a fixed width for metadata columns to keep them compact
      header: ({ column }) => <DataTableColumnHeader column={column} title="Scheduled" className="w-[140px]" />,
      cell: ({ row }) => {
        const date = row.getValue("assigned_date") as string;
        if (!date) return <span className="text-muted-foreground/30 text-xs">—</span>;
        return <span className="text-xs font-medium">{date}</span>;
      },
    },
    {
      accessorKey: "hard_deadline",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Deadline" className="w-[140px]" />,
      cell: ({ row }) => {
        const date = row.getValue("hard_deadline") as string;
        if (!date) return <span className="text-muted-foreground/30 text-xs">—</span>;
        return (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>{new Date(date).toLocaleDateString()}</span>
          </div>
        );
      },
    },
    {
      accessorKey: "created_at",
      // Set a fixed width for metadata columns to keep them compact
      header: ({ column }) => <DataTableColumnHeader column={column} title="Created" className="w-[140px]" />,
      cell: ({ row }) => {
        const date = row.getValue("created_at") as string;
        if (!date) return <span className="text-muted-foreground/30 text-xs">—</span>;
        return <span className="text-xs font-medium">{date}</span>;
      },
    },

    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Status" className="w-[120px]" />,
      cell: ({ row }) => {
        const status = row.getValue("status") as string;
        return (
          <Badge
            variant="outline"
            className={cn(
              "capitalize font-normal",
              status === 'completed' ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 'bg-blue-500/10 text-blue-600 border-blue-500/20'
            )}
          >
            {status.replace("_", " ")}
          </Badge>
        );
      },
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <Link href={`/dashboard/tasks/${row.original.id}/edit`}>
          <Edit2 className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-primary" />
        </Link>
      ),
    },
  ];
