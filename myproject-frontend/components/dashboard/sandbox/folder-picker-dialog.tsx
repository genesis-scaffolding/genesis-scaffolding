"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FolderIcon, FolderOpenIcon, Loader2 } from "lucide-react";
import { getFoldersAction } from "@/app/actions/sandbox";

interface FolderPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectFolder: (folderPath: string) => void;
  currentFolder?: string;
}

export function FolderPickerDialog({ open, onOpenChange, onSelectFolder, currentFolder }: FolderPickerDialogProps) {
  const [folders, setFolders] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = React.useState<string>(".");

  React.useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      getFoldersAction(".")
        .then((folds) => {
          setFolders(folds);
          setLoading(false);
        })
        .catch(() => {
          setError("Failed to load folders");
          setLoading(false);
        });
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Move to folder</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          {loading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : error ? (
            <div className="text-sm text-destructive text-center p-4">{error}</div>
          ) : (
            <div className="space-y-1">
              {/* Option: root */}
              <button
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-accent ${
                  selectedFolder === "." ? "bg-accent" : ""
                }`}
                onClick={() => setSelectedFolder(".")}
              >
                <FolderOpenIcon className="h-4 w-4" />
                <span>Sandbox root</span>
              </button>

              {/* Option: each subfolder */}
              {folders.map((folder) => {
                const isCurrentOrChild = folder === currentFolder || folder.startsWith(currentFolder + "/");
                if (isCurrentOrChild) return null;
                const folderName = folder.split("/").pop() || folder;
                return (
                  <button
                    key={folder}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-accent ${
                      selectedFolder === folder ? "bg-accent" : ""
                    }`}
                    onClick={() => setSelectedFolder(folder)}
                  >
                    <FolderIcon className="h-4 w-4" />
                    <span>{folderName}</span>
                    <span className="text-xs text-muted-foreground ml-auto">{folder}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => { onSelectFolder(selectedFolder); onOpenChange(false); }}>
            Move here
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
