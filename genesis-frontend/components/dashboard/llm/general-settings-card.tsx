"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { updateDefaultModelAction } from "@/app/actions/llm-config";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

interface Props {
  defaultModel: string;
  models: string[];
}

export function GeneralSettingsCard({ defaultModel, models }: Props) {
  const [value, setValue] = useState(defaultModel);
  const [isPending, setIsPending] = useState(false);

  async function handleSave() {
    setIsPending(true);
    try {
      await updateDefaultModelAction(value);
      toast.success("Default model updated");
    } catch (error: any) {
      toast.error(error.message);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-6 flex items-end gap-4">
        <div className="flex-1 min-w-0">
          <label className="text-sm font-medium mb-2 block">Primary Default Model</label>
          <Select value={value} onValueChange={setValue}>
            <SelectTrigger>
              <SelectValue placeholder="Select a model" />
            </SelectTrigger>
            <SelectContent>
              {models.map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          onClick={handleSave}
          disabled={isPending || value === defaultModel}
          className="shrink-0"
        >
          {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save
        </Button>
      </CardContent>
    </Card>
  );
}
