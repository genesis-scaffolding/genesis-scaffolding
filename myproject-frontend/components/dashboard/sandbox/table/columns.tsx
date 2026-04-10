"use client";

import { ColumnDef } from "@tanstack/react-table";
import { SandboxFile } from "@/types/sandbox";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import { Button } from "@/components/ui/button";
import { FileText, FileDown, Trash2 } from "lucide-react";
import Link from "next/link";
import { deleteFileAction } from "@/app/actions/sandbox";
import { toast } from "sonner";

export const getSandboxColumns = (onFileDeleted: (fileId: number) => void): ColumnDef<SandboxFile>[] => [
  {
    accessorKey: "filename",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Name" />,
    cell: ({ row }) => {
      const file = row.original;
      const isPdf = file.filename.endsWith(".pdf");
      return (
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg ${isPdf ? "bg-red-50 text-red-500" : "bg-blue-50 text-blue-500"}`}
          >
            <FileText className="h-4 w-4" />
          </div>
          <Link
            href={`/dashboard/sandbox/file/${file.id}`}
            className="font-medium text-sm truncate max-w-xs hover:text-primary transition-colors"
          >
            {file.filename}
          </Link>
        </div>
      );
    },
  },
  {
    accessorKey: "relative_path",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Path" className="w-[300px]" />,
    cell: ({ row }) => {
      const path = row.getValue("relative_path") as string;
      return (
        <code className="text-xs bg-slate-100 px-2 py-1 rounded text-slate-600 font-mono">
          {path}
        </code>
      );
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const file = row.original;
      return (
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              window.open(`/api/files/${file.id}/download`, "_blank");
            }}
          >
            <FileDown className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-destructive hover:bg-destructive/10"
            onClick={async () => {
              if (!confirm(`Are you sure you want to delete ${file.filename}?`)) return;
              try {
                await deleteFileAction(file.id);
                toast.success("File deleted");
                onFileDeleted(file.id);
              } catch (err) {
                toast.error("Failed to delete file");
              }
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      );
    },
  },
];
