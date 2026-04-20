'use client';

import { FileBrowserModal } from './file-browser-modal';
import { Button } from "@/components/ui/button";
import { FileText, X, FolderOpen } from "lucide-react";
import { SandboxFile } from '@/types/sandbox';

interface SandboxFilePickerProps {
  value: SandboxFile;
  onChange: (file: SandboxFile) => void;
  placeholder?: string;
}

export function SandboxFilePicker({ value, onChange, placeholder }: SandboxFilePickerProps) {
  // Logic: Only show the "Selected" state if value is a valid object with a path
  const hasValue = value && typeof value === 'object' && value.relative_path;

  return (
    <div className="space-y-2">
      {hasValue ? (
        <div className="flex items-center justify-between p-3 border rounded-lg bg-slate-50 border-primary/30">
          <div className="flex items-center gap-3 overflow-hidden">
            <FileText className="h-4 w-4 text-primary shrink-0" />
            <span className="text-sm font-mono truncate">{value.relative_path}</span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onChange(null as any)}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <FileBrowserModal
          onSelect={onChange}
          currentValue={typeof value === 'string' ? value : value?.relative_path}
          trigger={
            <Button type="button" variant="outline" className="w-full justify-start text-muted-foreground border-dashed h-12">
              <FolderOpen className="mr-2 h-4 w-4" />
              {placeholder || "Select file..."}
            </Button>
          }
        />
      )}
    </div>
  );
}
