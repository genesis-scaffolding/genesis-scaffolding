"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Cpu, Plus, Settings2, Trash2, Star } from "lucide-react";
import { ModelDialog } from "./model-dialog";
import { deleteModelAction } from "@/app/actions/llm-config";
import { toast } from "sonner";
import { LLMModelConfig } from "@/types/llm";
import { cn } from "@/lib/utils";

interface ModelSectionProps {
  models: Record<string, LLMModelConfig>;
  providers: string[];
}

export function ModelSection({ models, providers }: ModelSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editing, setEditing] = useState<{ nickname: string; data: LLMModelConfig } | null>(null);

  const onEdit = (nickname: string, data: LLMModelConfig) => {
    setEditing({ nickname, data });
    setIsOpen(true);
  };

  const onDelete = async (nickname: string) => {
    if (!confirm(`Are you sure you want to delete model "${nickname}"?`)) return;
    try {
      await deleteModelAction(nickname);
      toast.success("Model deleted");
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {Object.entries(models).map(([nickname, data]) => (
          <div
            key={nickname}
            className="flex items-center justify-between p-4 border rounded-xl bg-card shadow-sm hover:border-primary/20 transition-colors group"
          >
            {/* Flex-Fix: min-w-0 allows the title to truncate if the screen is narrow */}
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <div className="bg-secondary p-2 rounded-lg shrink-0">
                <Cpu className="w-5 h-5 text-secondary-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold truncate">{nickname}</h4>
                  <span className="text-[10px] uppercase tracking-wider bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-bold shrink-0">
                    {data.provider}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground truncate font-mono mt-0.5">
                  {data.model}
                </p>
              </div>
            </div>

            {/* Actions: shrink-0 ensures buttons are never squashed */}
            <div className="flex items-center gap-1 shrink-0 ml-4">
              <Button
                variant="ghost"
                size="icon"
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => onEdit(nickname, data)}
              >
                <Settings2 className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => onDelete(nickname)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}

        {Object.keys(models).length === 0 && (
          <div className="py-12 border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-muted-foreground bg-muted/10">
            <Cpu className="w-8 h-8 mb-2 opacity-20" />
            <p className="text-sm">No models configured yet.</p>
          </div>
        )}
      </div>

      <Button
        variant="outline"
        className="w-full border-dashed py-6"
        onClick={() => { setEditing(null); setIsOpen(true); }}
      >
        <Plus className="w-4 h-4 mr-2" /> Add New Model Configuration
      </Button>

      {/* The Dialog for Create/Update */}
      <ModelDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        editing={editing}
        providers={providers}
      />
    </div>
  );
}
