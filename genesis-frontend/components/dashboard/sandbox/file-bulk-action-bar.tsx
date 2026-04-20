"use client";

import * as React from "react";
import { FolderInput, Trash2, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileBulkActionBarProps {
  selectedFiles: { relative_path: string; name: string; is_dir: boolean }[];
  onClear: () => void;
  onMove: (destinationFolder: string) => void;  // called when user clicks Move — parent opens dialog
  onDelete: () => Promise<void>;  // parent handles the actual delete
  className?: string;
}

export function FileBulkActionBar({
  selectedFiles,
  onClear,
  onMove,
  onDelete,
  className,
}: FileBulkActionBarProps) {
  const [isPending, setIsPending] = React.useState(false);

  // Only files can be moved (not directories)
  const filesToMove = selectedFiles.filter((f) => !f.is_dir);

  if (selectedFiles.length === 0) return null;

  async function handleDelete() {
    if (!confirm(`Delete ${selectedFiles.length} item(s)?`)) return;
    setIsPending(true);
    try {
      await onDelete();
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className={cn(
      "fixed left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4",
      className ?? "bottom-6"
    )}>
      <div className="bg-primary text-primary-foreground px-3 py-3 md:py-2 rounded-3xl md:rounded-full shadow-2xl flex flex-col md:flex-row items-stretch md:items-center gap-2 md:gap-0 border border-primary-foreground/20">

        {/* Selection count */}
        <div className="flex items-center justify-center px-2 py-1 md:py-0">
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <span className="text-xs font-bold whitespace-nowrap">
              {selectedFiles.length} Selected
            </span>
          )}
        </div>

        <div className="hidden md:block h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Move — signals parent to open folder picker */}
        <Button
          variant="ghost"
          size="sm"
          className="h-9 px-3 rounded-full hover:bg-primary-foreground/10 gap-2 font-medium"
          onClick={() => onMove("")}
          disabled={isPending || filesToMove.length === 0}
        >
          <FolderInput className="h-4 w-4" />
          <span>Move</span>
        </Button>

        <div className="hidden md:block h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Delete */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full hover:bg-destructive hover:text-destructive-foreground text-red-400"
          onClick={handleDelete}
          disabled={isPending}
        >
          <Trash2 className="h-5 w-5" />
        </Button>

        {/* Close */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClear}
          disabled={isPending}
          className="h-9 w-9 rounded-full hover:bg-primary-foreground/10"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
