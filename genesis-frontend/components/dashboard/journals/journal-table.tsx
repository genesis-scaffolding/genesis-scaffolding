"use client";

import * as React from "react";
import { JournalEntry, Project } from "@/types/productivity";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getJournalColumns } from "./table/columns";
import { SortingState, VisibilityState } from "@tanstack/react-table";

interface JournalTableProps {
  entries: JournalEntry[];
  projects: Project[];
  hiddenColumns?: VisibilityState;
}

export function JournalTable({ entries, projects, hiddenColumns = {} }: JournalTableProps) {
  const columns = React.useMemo(
    () => getJournalColumns(projects),
    [projects]
  );

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "reference_date", desc: true }],
    []
  );

  const initialVisibility = React.useMemo(
    () => ({ ...hiddenColumns }),
    [hiddenColumns]
  );

  return (
    <DataTable
      data={entries}
      columns={columns}
      getRowId={(row: JournalEntry) => row.id.toString()}
      initialSorting={defaultSorting}
      initialColumnVisibility={initialVisibility}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
