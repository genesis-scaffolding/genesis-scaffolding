"use client";

import * as React from "react";
import { Task, Project } from "@/types/productivity";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getTaskColumns } from "./table/columns";
import { TaskTableToolbar } from "./table/toolbar";
import { BulkActionBar } from "./bulk-action-bar";
import { SortingState } from "@tanstack/react-table";

interface TaskTableProps {
  tasks: Task[];
  projects: Project[];
  variant?: "table" | "list" | "dashboard";
  floatingOffset?: boolean;
  pagination?: boolean;
}

export function TaskTable({
  tasks,
  projects,
  variant = "table",
  floatingOffset = false,
  pagination,
}: TaskTableProps) {
  const enablePagination = pagination ?? variant === "table";

  const columns = React.useMemo(() => getTaskColumns(projects, variant), [projects, variant]);

  const initialVisibility = React.useMemo(() => ({
    project: variant !== "list" && variant !== "dashboard",
    created_at: false,
    scheduled_start: false,
    assigned_date: variant !== "dashboard",
    hard_deadline: variant !== "dashboard",
  }), [variant]);

  const defaultSorting: SortingState = React.useMemo(() => [
    {
      id: "status",
      desc: true, // Show 'To Do' before 'Done'
    },
    {
      id: "hard_deadline",
      desc: false, // Soonest tasks first
    },
    {
      id: "assigned_date",
      desc: variant === "dashboard",
    },
    {
      id: "scheduled_start",
      desc: variant === "dashboard",
    },
    {
      id: "created_at",
      desc: false, // Oldest tasks first
    }
  ], []);

  return (
    <DataTable
      data={tasks}
      columns={columns}
      initialSorting={defaultSorting}
      enableMultiSort={true}
      initialColumnVisibility={initialVisibility}
      getRowId={(row: Task) => row.id.toString()}
      enablePagination={enablePagination}
      defaultPageSize={20}
      renderToolbar={(table) => <TaskTableToolbar table={table} />}
      renderFloatingBar={(table) => {
        const selectedRows = table.getFilteredSelectedRowModel().rows;
        const selectedIds = selectedRows.map((row) => (row.original as Task).id);

        return (
          <BulkActionBar
            selectedIds={selectedIds}
            onClear={() => table.resetRowSelection()}
            projects={projects}
            className={floatingOffset ? "bottom-24" : "bottom-6"}
          />
        );
      }}
    />
  );
}
