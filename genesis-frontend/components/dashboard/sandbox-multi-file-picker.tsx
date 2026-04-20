'use client';

import { FileBrowserModal } from './file-browser-modal';
import { Button } from "@/components/ui/button";
import { FileText, X, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SandboxFile } from "@/types/sandbox";

interface SandboxMultiFilePickerProps {
  value: SandboxFile[];
  onChange: (value: SandboxFile[]) => void;
  placeholder?: string;
}

export function SandboxMultiFilePicker({ value = [], onChange, placeholder }: SandboxMultiFilePickerProps) {

  const addFile = (file: SandboxFile) => {
    const currentFiles = Array.isArray(value) ? value : [];

    if (!currentFiles.find(f => f.relative_path === file.relative_path)) {
      onChange([...currentFiles, file]);
    }
  };

  const removeFile = (relativePathToRemove: string) => {
    onChange(value.filter(f => f.relative_path !== relativePathToRemove));
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {Array.isArray(value) && value.map((file) => {
          if (!file || typeof file !== 'object') return null;
          return (

            <Badge
              key={file.relative_path}
              variant="secondary"
              className="pl-2 pr-1 py-1 gap-2 border-primary/20 bg-primary/5"
            >
              <div className="flex items-center gap-1.5 overflow-hidden">
                <FileText className="h-3 w-3 text-primary" />
                <span className="text-xs font-mono max-w-[200px] truncate">
                  {file.relative_path}
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeFile(file.relative_path)}
                className="hover:bg-primary/10 rounded-full p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )
        }
        )}
      </div>

      <FileBrowserModal
        onSelect={addFile}
        trigger={
          <Button type="button" variant="outline" size="sm" className="w-full border-dashed">
            <Plus className="mr-2 h-4 w-4" />
            {value.length > 0 ? "Add another file..." : placeholder || "Select files..."}
          </Button>
        }
      />
    </div>
  );
}
