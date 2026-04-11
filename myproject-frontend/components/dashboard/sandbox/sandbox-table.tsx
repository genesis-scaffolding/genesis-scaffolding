"use client";

import * as React from "react";
import { Table as TableType } from "@tanstack/react-table";
import { SandboxFile } from "@/types/sandbox";
import { DataTable } from "@/components/dashboard/shared/data-table/data-table";
import { getSandboxColumns } from "./table/columns";

interface SandboxTableProps {
  files: SandboxFile[];
  onFileDeleted: (relativePath: string) => void;
  renderFloatingBar?: (table: TableType<SandboxFile>) => React.ReactNode;
}

export function SandboxTable({ files, onFileDeleted, renderFloatingBar }: SandboxTableProps) {
  const columns = React.useMemo(
    () => getSandboxColumns({ onFileDeleted }),
    [onFileDeleted]
  );

  return (
    <DataTable
      data={files}
      columns={columns}
      getRowId={(row: SandboxFile) => row.relative_path}
      enablePagination={true}
      defaultPageSize={20}
      renderFloatingBar={renderFloatingBar}
    />
  );
}
