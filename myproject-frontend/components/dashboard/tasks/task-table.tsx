"use client";

import * as React from "react";
import { Task, Project } from "@/types/productivity";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getTaskColumns } from "./table/columns";
import { TaskTableToolbar } from "./table/toolbar";
import { BulkActionBar } from "./bulk-action-bar";

interface TaskTableProps {
  tasks: Task[];
  projects: Project[];
  variant?: "table" | "list"; // Use 'list' for the project detail view
}

export function TaskTable({ tasks, projects, variant = "table" }: TaskTableProps) {
  const columns = React.useMemo(() => getTaskColumns(projects, variant), [projects, variant]);

  const initialVisibility = React.useMemo(() => ({
    // If we are looking at a single project list, hide the project column by default
    project: variant !== "list",
  }), [variant]);

  return (
    <DataTable
      data={tasks}
      columns={columns}
      initialColumnVisibility={initialVisibility}
      getRowId={(row: Task) => row.id.toString()}
      // 2. The Render Prop: We get the 'table' from DataTable and pass it to our specific Toolbar
      renderToolbar={(table) => <TaskTableToolbar table={table} />}

      // 3. Handle the Bulk Actions bar the same way
      renderFloatingBar={(table) => {
        const selectedRows = table.getFilteredSelectedRowModel().rows;
        const selectedIds = selectedRows.map((row) => (row.original as Task).id);

        return (
          <BulkActionBar
            selectedIds={selectedIds}
            onClear={() => table.resetRowSelection()}
            projects={projects}
          />
        );
      }}
    />
  );
}
