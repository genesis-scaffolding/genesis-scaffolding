"use client";

import { ColumnDef, Row } from "@tanstack/react-table";
import { WorkflowJob, JobStatus } from "@/types/job";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import { CheckCircle2, AlertCircle, PlayCircle, Clock, ChevronRight } from "lucide-react";
import { formatRelativeTime } from "@/lib/date-utils";
import Link from "next/link";

/**
 * Custom sorting function that forces null/undefined values to the bottom
 * for date columns (created_at, updated_at).
 */
const dateSortingWithNullsLast = (rowA: Row<WorkflowJob>, rowB: Row<WorkflowJob>, columnId: string) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;

  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;

  const dateA = new Date(a).getTime();
  const dateB = new Date(b).getTime();

  return dateA - dateB;
};

/**
 * Status weight sorting for consistent ordering.
 */
const STATUS_WEIGHTS: Record<JobStatus, number> = {
  running: 4,
  pending: 3,
  failed: 2,
  completed: 1,
};

const statusSortingFn = (rowA: Row<WorkflowJob>, rowB: Row<WorkflowJob>, columnId: string) => {
  const statusA = rowA.getValue(columnId) as JobStatus;
  const statusB = rowB.getValue(columnId) as JobStatus;
  return (STATUS_WEIGHTS[statusA] ?? 0) - (STATUS_WEIGHTS[statusB] ?? 0);
};

const getStatusIcon = (status: JobStatus) => {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case "failed":
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    case "running":
      return <PlayCircle className="w-4 h-4 text-blue-500 animate-pulse" />;
    default:
      return <Clock className="w-4 h-4 text-slate-400" />;
  }
};

export const getJobsColumns = (): ColumnDef<WorkflowJob>[] => [
  {
    accessorKey: "id",
    header: ({ column }) => <DataTableColumnHeader column={column} title="ID" className="w-[80px]" />,
    cell: ({ row }) => {
      const id = row.getValue("id") as number;
      return <span className="font-mono text-xs text-muted-foreground">#{id}</span>;
    },
  },
  {
    accessorKey: "workflow_id",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Workflow" />,
    cell: ({ row }) => {
      const workflowId = row.getValue("workflow_id") as string;
      return <span className="font-medium">{workflowId.replace(/_/g, " ")}</span>;
    },
  },
  {
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" className="w-[120px]" />,
    sortingFn: statusSortingFn,
    cell: ({ row }) => {
      const status = row.getValue("status") as JobStatus;
      return (
        <div className="flex items-center gap-2">
          {getStatusIcon(status)}
          <span className="capitalize text-sm">{status}</span>
        </div>
      );
    },
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Created" className="w-[150px]" />,
    sortingFn: dateSortingWithNullsLast,
    cell: ({ row }) => {
      const createdAt = row.getValue("created_at") as string;
      return (
        <span className="text-sm text-muted-foreground">
          {formatRelativeTime(createdAt)}
        </span>
      );
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const job = row.original;
      return (
        <Link
          href={`/dashboard/jobs/${job.id}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          Details <ChevronRight className="w-4 h-4" />
        </Link>
      );
    },
  },
];
