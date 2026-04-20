"use client";

import * as React from "react";
import { WorkflowJob } from "@/types/job";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getJobsColumns } from "./table/columns";
import { SortingState } from "@tanstack/react-table";

interface JobsTableProps {
  jobs: WorkflowJob[];
}

export function JobsTable({ jobs }: JobsTableProps) {
  const columns = React.useMemo(() => getJobsColumns(), []);

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "created_at", desc: true }],
    []
  );

  return (
    <DataTable
      data={jobs}
      columns={columns}
      getRowId={(row: WorkflowJob) => row.id.toString()}
      initialSorting={defaultSorting}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
