"use client";

import * as React from "react";
import { JournalEntry, Project } from "@/types/productivity";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getJournalColumns } from "./table/columns";
import { SortingState } from "@tanstack/react-table";

interface JournalTableProps {
  entries: JournalEntry[];
  projects: Project[];
}

export function JournalTable({ entries, projects }: JournalTableProps) {
  const columns = React.useMemo(
    () => getJournalColumns(projects),
    [projects]
  );

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "reference_date", desc: true }],
    []
  );

  return (
    <DataTable
      data={entries}
      columns={columns}
      getRowId={(row: JournalEntry) => row.id.toString()}
      initialSorting={defaultSorting}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
