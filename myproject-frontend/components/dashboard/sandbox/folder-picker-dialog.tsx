"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FolderIcon, FolderOpenIcon, Loader2 } from "lucide-react";
import { getFoldersAction, createFolderAction } from "@/app/actions/sandbox";

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
  const [newFolderName, setNewFolderName] = React.useState<string>("");
  const [creating, setCreating] = React.useState<boolean>(false);
  const [createError, setCreateError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      setSelectedFolder(".");
      setNewFolderName("");
      setCreating(false);
      setCreateError(null);
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

  async function handleCreateFolder() {
    if (!newFolderName.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const dest = currentFolder === "." ? newFolderName.trim() : `${currentFolder}/${newFolderName.trim()}`;
      const created = await createFolderAction(dest);
      onSelectFolder(created.relative_path);
    } catch (err) {
      setCreateError("Failed to create folder");
    } finally {
      setCreating(false);
    }
  }

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
            <>
              <div className="flex gap-2 mb-3">
                <Input
                  placeholder="New folder name..."
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                />
                <Button size="sm" onClick={handleCreateFolder} disabled={creating || !newFolderName.trim()}>
                  {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create"}
                </Button>
              </div>
              {createError && <p className="text-xs text-destructive mb-2">{createError}</p>}
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
                const isCurrentOrChild = folder === currentFolder || folder.startsWith(currentFolder ? currentFolder + "/" : "");
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
            </>
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
