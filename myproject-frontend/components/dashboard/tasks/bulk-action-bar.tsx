"use client";

import { Button } from "@/components/ui/button";
import { CheckCircle2, FolderInput, Trash2, X } from "lucide-react";
import { bulkUpdateTasksAction } from "@/app/actions/productivity";
import { useRouter } from "next/navigation";

interface BulkActionBarProps {
  selectedIds: number[];
  onClear: () => void;
}

export function BulkActionBar({ selectedIds, onClear }: BulkActionBarProps) {
  const router = useRouter();
  if (selectedIds.length === 0) return null;

  async function handleBulkStatus(statusValue: 'completed' | 'todo' | 'in_progress') {
    try {
      await bulkUpdateTasksAction({
        ids: selectedIds,
        updates: { status: statusValue }
      });
      onClear();
      router.refresh();
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4">
      <div className="bg-primary text-primary-foreground px-4 py-2 rounded-full shadow-2xl flex items-center gap-4 border border-primary-foreground/20">
        <span className="text-sm font-bold mr-2">{selectedIds.length} Selected</span>

        <div className="h-4 w-px bg-primary-foreground/30" />

        <Button
          variant="ghost"
          size="sm"
          className="hover:bg-primary-foreground/10 h-8"
          onClick={() => handleBulkStatus('completed')}
        >
          <CheckCircle2 className="h-4 w-4 mr-2" /> Mark Done
        </Button>

        {/* Note: Project migration dropdown can be added here later */}

        <Button variant="ghost" size="sm" onClick={onClear} className="h-8">
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
