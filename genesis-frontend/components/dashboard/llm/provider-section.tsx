"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, ShieldCheck, Trash2, Settings2 } from "lucide-react";
import { ProviderDialog } from "./provider-dialog";
import { deleteProviderAction } from "@/app/actions/llm-config";
import { toast } from "sonner";
import { LLMProvider } from "@/types/llm";

export function ProviderSection({ providers }: { providers: Record<string, LLMProvider> }) {
  const [isOpen, setIsOpen] = useState(false);
  const [editing, setEditing] = useState<{ nickname: string; data: LLMProvider } | null>(null);

  const onEdit = (nickname: string, data: LLMProvider) => {
    setEditing({ nickname, data });
    setIsOpen(true);
  };

  const onDelete = async (nickname: string) => {
    if (!confirm(`Are you sure you want to delete provider "${nickname}"?`)) return;
    try {
      await deleteProviderAction(nickname);
      toast.success("Provider deleted");
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {Object.entries(providers).map(([nickname, data]) => (
          <div key={nickname} className="flex items-center justify-between p-4 border rounded-xl bg-card shadow-sm">
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <ShieldCheck className="w-5 h-5 text-primary shrink-0" />
              <div className="min-w-0 flex-1">
                <h4 className="font-semibold truncate">{nickname}</h4>
                <p className="text-xs text-muted-foreground truncate italic">{data.base_url || "Default API"}</p>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0 ml-4">
              <Button variant="ghost" size="icon" onClick={() => onEdit(nickname, data)}>
                <Settings2 className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="text-destructive" onClick={() => onDelete(nickname)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
      <Button variant="outline" className="w-full border-dashed" onClick={() => { setEditing(null); setIsOpen(true); }}>
        <Plus className="w-4 h-4 mr-2" /> Add Provider
      </Button>
      <ProviderDialog open={isOpen} onOpenChange={setIsOpen} editing={editing} />
    </div>
  );
}
