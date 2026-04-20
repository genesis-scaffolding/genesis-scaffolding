"use client";

import * as React from "react";
import { ChatSession } from "@/types/chat";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getChatHistoryColumns } from "./table/columns";
import { SortingState } from "@tanstack/react-table";

interface ChatHistoryTableProps {
  sessions: ChatSession[];
}

export function ChatHistoryTable({ sessions }: ChatHistoryTableProps) {
  const columns = React.useMemo(() => getChatHistoryColumns(), []);

  const defaultSorting: SortingState = React.useMemo(
    () => [{ id: "updated_at", desc: true }],
    []
  );

  return (
    <DataTable
      data={sessions}
      columns={columns}
      getRowId={(row: ChatSession) => row.id.toString()}
      initialSorting={defaultSorting}
      enablePagination={true}
      defaultPageSize={20}
    />
  );
}
