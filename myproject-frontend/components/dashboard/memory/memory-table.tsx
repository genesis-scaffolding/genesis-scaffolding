"use client";

import * as React from "react";
import { EventLog, TopicalMemory } from "@/types/memory";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getMemoryColumns } from "./table/columns";
import { SortingState } from "@tanstack/react-table";

interface MemoryTableProps {
  events: EventLog[];
  topics: TopicalMemory[];
}

export function MemoryTable({ events, topics }: MemoryTableProps) {
  const columns = React.useMemo(() => getMemoryColumns(), []);

  // Combine events and topics for the table
  const combinedData = React.useMemo(() => {
    return [...events, ...topics];
  }, [events, topics]);

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "created_at", desc: true }],
    []
  );

  return (
    <DataTable
      data={combinedData}
      columns={columns}
      getRowId={(row: EventLog | TopicalMemory) => {
        const type = "event_time" in row ? "event" : "topic";
        return `${type}-${row.id}`;
      }}
      initialSorting={defaultSorting}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
