"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { SandboxFile } from "@/types/sandbox";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { StandaloneUploadButton } from "./standalone-upload-button";
import { SandboxTable } from "./sandbox/sandbox-table";
import { FolderPickerDialog } from "./sandbox/folder-picker-dialog";
import { FileBulkActionBar } from "./sandbox/file-bulk-action-bar";
import { moveFilesAction, deleteFileAction } from "@/app/actions/sandbox";
import { Table as TableType } from "@tanstack/react-table";
import { toast } from "sonner";

interface SandboxFileExplorerProps {
  allFiles: SandboxFile[];
  allFolders: string[];
  folder?: string;
}

export function SandboxFileExplorer({ allFiles, allFolders, folder }: SandboxFileExplorerProps) {
  const [files, setFiles] = React.useState(allFiles);
  const [search, setSearch] = React.useState("");
  const [showFolderPicker, setShowFolderPicker] = React.useState(false);
  const router = useRouter();
  // Keep a stable ref to the latest table instance so async callbacks can read it
  const tableRef = React.useRef<TableType<SandboxFile> | null>(null);

  React.useEffect(() => {
    setFiles(allFiles);
  }, [allFiles]);

  // Compute sub-folders of the current folder
  const subFolders = React.useMemo(() => {
    if (!folder || folder === ".") {
      // Top level: folders that don't contain "/"
      return allFolders.filter((f) => !f.includes("/"));
    }
    // Sub-folders: those that start with "folder/" prefix
    const prefix = folder + "/";
    return allFolders
      .filter((f) => f.startsWith(prefix))
      .map((f) => f.slice(prefix.length))
      .filter((f) => !f.includes("/")); // Only immediate children
  }, [allFolders, folder]);

  // Transform sub-folders into SandboxFile objects for the table
  const folderRows = React.useMemo((): SandboxFile[] => {
    return subFolders.map((folderName): SandboxFile => {
      const folderPath = folder ? `${folder}/${folderName}` : folderName;
      return {
        relative_path: folderPath,
        name: folderName,
        is_dir: true,
        size: null,
        mime_type: null,
        mtime: null,
        created_at: null,
      };
    });
  }, [subFolders, folder]);

  // Filter files in current folder
  const filesInFolder = React.useMemo(() => {
    if (!folder || folder === ".") return files;
    return files.filter((f) => {
      const lastSlash = f.relative_path.lastIndexOf('/');
      const parentPath = lastSlash > 0 ? f.relative_path.substring(0, lastSlash) : "";
      return parentPath === folder;
    });
  }, [files, folder]);

  // Combine folders and files, filtered by search
  const combinedRows = React.useMemo(() => {
    const allRows = [...folderRows, ...filesInFolder];
    if (!search) return allRows;
    return allRows.filter((f) =>
      f.name && f.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [folderRows, filesInFolder, search]);

  const handleFileDeleted = React.useCallback((relativePath: string) => {
    setFiles((prev) => prev.filter((f) => f.relative_path !== relativePath));
  }, []);

  const handleUploadSuccess = React.useCallback((newFile: SandboxFile) => {
    setFiles((prev) => [newFile, ...prev]);
  }, []);

  async function handleMoveFiles(destFolder: string) {
    const table = tableRef.current;
    if (!table) return;
    const selected = table.getFilteredSelectedRowModel().rows.map((r) => r.original);
    const paths = selected.filter((f) => !f.is_dir).map((f) => f.relative_path);
    if (paths.length === 0) return;

    try {
      await moveFilesAction(paths, destFolder);
      toast.success(`Moved ${paths.length} file(s)`);
    } catch (err) {
      toast.error("Failed to move files");
    }
  }

  const handleDeleteFiles = React.useCallback(async () => {
    const table = tableRef.current;
    if (!table) return;
    const selected = table.getFilteredSelectedRowModel().rows.map((r) => r.original);
    for (const file of selected) {
      await deleteFileAction(file.relative_path);
    }
    toast.success(`Deleted ${selected.length} item(s)`);
  }, []);

  // useCallback so the function reference is stable across renders.
  // The tableRef is synced via useEffect to avoid calling setState during render.
  const renderFloatingBar = React.useCallback((table: TableType<SandboxFile>) => {
    tableRef.current = table;
    const selected = table.getFilteredSelectedRowModel().rows.map((r) => r.original);
    return (
      <FileBulkActionBar
        selectedFiles={selected}
        onClear={() => {
          table.resetRowSelection();
        }}
        onMove={() => setShowFolderPicker(true)}
        onDelete={handleDeleteFiles}
      />
    );
  }, [handleDeleteFiles]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 bg-white p-4 rounded-xl border shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sandbox..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <StandaloneUploadButton onSuccess={handleUploadSuccess} />
      </div>

      <SandboxTable
        files={combinedRows}
        onFileDeleted={handleFileDeleted}
        renderFloatingBar={renderFloatingBar}
      />

      <FolderPickerDialog
        open={showFolderPicker}
        onOpenChange={setShowFolderPicker}
        allFolders={allFolders}
        onSelectFolder={(destFolder) => {
          setShowFolderPicker(false);
          handleMoveFiles(destFolder).then(() => router.refresh());
        }}
        currentFolder={folder}
      />
    </div>
  );
}
