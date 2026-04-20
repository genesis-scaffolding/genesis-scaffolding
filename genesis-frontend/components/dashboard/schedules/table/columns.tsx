"use client";

import { ColumnDef, Row } from "@tanstack/react-table";
import { WorkflowSchedule } from "@/types/schedule";
import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, Trash2 } from "lucide-react";
import { updateScheduleAction, deleteScheduleAction } from "@/app/actions/schedule";
import { formatRelativeTime } from "@/lib/date-utils";
import Link from "next/link";
import { toast } from "sonner";

/**
 * Custom sorting function that forces null/undefined values to the bottom
 * for date columns (last_run_at).
 */
const dateSortingWithNullsLast = (rowA: Row<WorkflowSchedule>, rowB: Row<WorkflowSchedule>, columnId: string) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;

  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;

  const dateA = new Date(a).getTime();
  const dateB = new Date(b).getTime();

  return dateA - dateB;
};

export const getScheduleColumns = (): ColumnDef<WorkflowSchedule>[] => [
  {
    accessorKey: "enabled",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" className="w-[80px]" />,
    cell: ({ row }) => {
      const schedule = row.original;
      return (
        <Switch
          checked={schedule.enabled}
          onCheckedChange={async () => {
            try {
              await updateScheduleAction(schedule.id, { enabled: !schedule.enabled });
              toast.success(`Schedule ${!schedule.enabled ? "enabled" : "disabled"}`);
            } catch (err) {
              toast.error("Failed to update schedule");
            }
          }}
        />
      );
    },
  },
  {
    accessorKey: "name",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Name" />,
    cell: ({ row }) => {
      const schedule = row.original;
      return (
        <Link
          href={`/dashboard/schedules/${schedule.id}`}
          className="hover:underline hover:text-primary transition-colors"
        >
          {schedule.name}
        </Link>
      );
    },
  },
  {
    accessorKey: "workflow_id",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Workflow" className="w-[150px]" />,
    cell: ({ row }) => {
      const workflowId = row.getValue("workflow_id") as string;
      return (
        <Badge variant="outline" className="font-mono">
          {workflowId}
        </Badge>
      );
    },
  },
  {
    accessorKey: "cron_expression",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Frequency (Cron)" className="w-[200px]" />,
    cell: ({ row }) => {
      const schedule = row.original;
      return (
        <div className="flex items-center gap-2 text-sm">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <code className="bg-muted px-1 rounded">{schedule.cron_expression}</code>
          <span className="text-xs text-muted-foreground">({schedule.timezone})</span>
        </div>
      );
    },
  },
  {
    accessorKey: "last_run_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Run" className="w-[150px]" />,
    sortingFn: dateSortingWithNullsLast,
    cell: ({ row }) => {
      const lastRunAt = row.getValue("last_run_at") as string | null;
      if (!lastRunAt) return <span className="text-muted-foreground">Never</span>;
      return (
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {formatRelativeTime(lastRunAt)}
        </div>
      );
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const schedule = row.original;
      return (
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="icon"
            onClick={async () => {
              if (!confirm("Are you sure you want to delete this schedule?")) return;
              try {
                await deleteScheduleAction(schedule.id);
                toast.success("Schedule deleted");
              } catch (err) {
                toast.error("Failed to delete schedule");
              }
            }}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      );
    },
  },
];
