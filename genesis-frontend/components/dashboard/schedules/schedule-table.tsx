"use client";

import * as React from "react";
import { WorkflowSchedule } from "@/types/schedule";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getScheduleColumns } from "./table/columns";
import { SortingState } from "@tanstack/react-table";

interface ScheduleTableProps {
  schedules: WorkflowSchedule[];
}

export function ScheduleTable({ schedules }: ScheduleTableProps) {
  const columns = React.useMemo(() => getScheduleColumns(), []);

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "name", desc: false }],
    []
  );

  return (
    <DataTable
      data={schedules}
      columns={columns}
      getRowId={(row: WorkflowSchedule) => row.id.toString()}
      initialSorting={defaultSorting}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
