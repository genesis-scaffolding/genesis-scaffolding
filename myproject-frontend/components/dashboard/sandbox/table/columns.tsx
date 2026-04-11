"use client";

import { ColumnDef } from "@tanstack/react-table";
import { SandboxFile, encodeFileId } from "@/types/sandbox";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FileText, FileDown, Trash2, Folder } from "lucide-react";
import Link from "next/link";
import { deleteFileAction } from "@/app/actions/sandbox";
import { toast } from "sonner";

export interface SandboxColumnOptions {
  onFileDeleted: (relativePath: string) => void;
}

export function getSandboxColumns(options: SandboxColumnOptions): ColumnDef<SandboxFile>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          onClick={(e) => e.stopPropagation()}
          aria-label="Select row"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Name" />,
      cell: ({ row }) => {
        const file = row.original;
        if (file.is_dir) {
          return (
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-50 text-purple-500">
                <Folder className="h-4 w-4" />
              </div>
              <Link
                href={`/dashboard/files?folder=${file.relative_path}`}
                className="font-medium text-sm truncate max-w-xs hover:text-primary transition-colors"
              >
                {file.name}
              </Link>
            </div>
          );
        }
        const isPdf = file.name.endsWith(".pdf");
        return (
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${isPdf ? "bg-red-50 text-red-500" : "bg-blue-50 text-blue-500"}`}
            >
              <FileText className="h-4 w-4" />
            </div>
            <Link
              href={`/dashboard/files/${encodeFileId(file.relative_path)}`}
              className="font-medium text-sm truncate max-w-xs hover:text-primary transition-colors"
            >
              {file.name}
            </Link>
          </div>
        );
      },
    },
    {
      accessorKey: "relative_path",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Path" className="w-[300px]" />,
      cell: ({ row }) => {
        const file = row.original;
        if (file.is_dir) {
          return (
            <code className="text-xs bg-purple-50 px-2 py-1 rounded text-purple-600 font-mono">
              {file.relative_path}
            </code>
          );
        }
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
        // No actions for directories
        if (file.is_dir) {
          return null;
        }
        const encodedId = encodeFileId(file.relative_path);
        return (
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                window.open(`/api/files/${encodedId}/download`, "_blank");
              }}
            >
              <FileDown className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive hover:bg-destructive/10"
              onClick={async () => {
                if (!confirm(`Are you sure you want to delete ${file.name}?`)) return;
                try {
                  await deleteFileAction(file.relative_path);
                  toast.success("File deleted");
                  options.onFileDeleted(file.relative_path);
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
}
