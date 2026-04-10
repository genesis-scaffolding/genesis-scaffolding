"use client";

import * as React from "react";
import { SandboxFile } from "@/types/sandbox";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { StandaloneUploadButton } from "./standalone-upload-button";
import { SandboxTable } from "./sandbox/sandbox-table";
import Link from "next/link";
import { Folder } from "lucide-react";

interface SandboxFileExplorerProps {
  allFiles: SandboxFile[];
  allFolders: string[];
  folder?: string;
}

export function SandboxFileExplorer({ allFiles, allFolders, folder }: SandboxFileExplorerProps) {
  const [files, setFiles] = React.useState(allFiles);
  const [search, setSearch] = React.useState("");

  React.useEffect(() => {
    setFiles(allFiles);
  }, [allFiles]);

  const filteredFiles = React.useMemo(() => {
    return files.filter((f) =>
      f.filename.toLowerCase().includes(search.toLowerCase())
    );
  }, [files, search]);

  // Filter to current folder
  const filesInFolder = React.useMemo(() => {
    if (!folder) return filteredFiles;
    return filteredFiles.filter((f) => f.folder === folder);
  }, [filteredFiles, folder]);

  // Compute sub-folders of the current folder
  const subFolders = React.useMemo(() => {
    if (!folder) {
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

  const handleFileDeleted = React.useCallback((fileId: number) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  const handleUploadSuccess = React.useCallback((newFile: SandboxFile) => {
    setFiles((prev) => [newFile, ...prev]);
  }, []);

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

      {/* Folder navigation */}
      {subFolders.length > 0 && (
        <div className="flex flex-wrap gap-2 p-4 bg-white rounded-xl border shadow-sm">
          {subFolders.map((folderName) => {
            const href = folder ? `${folder}/${folderName}` : folderName;
            return (
              <Link
                key={folderName}
                href={`/dashboard/sandbox?folder=${href}`}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-sm font-medium transition-colors"
              >
                <Folder className="h-4 w-4 text-muted-foreground" />
                {folderName}
              </Link>
            );
          })}
        </div>
      )}

      <SandboxTable files={filesInFolder} onFileDeleted={handleFileDeleted} />
    </div>
  );
}
