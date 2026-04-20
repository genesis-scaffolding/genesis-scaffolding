"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage, FormDescription } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { saveModelAction } from "@/app/actions/llm-config";
import { toast } from "sonner";
import { useEffect } from "react";

const modelSchema = z.object({
  nickname: z.string().min(1, "Nickname is required"),
  provider: z.string().min(1, "Provider is required"),
  model: z.string().min(1, "Model string is required"),
  params_json: z.string().refine((val) => {
    try { JSON.parse(val); return true; } catch { return false; }
  }, "Invalid JSON format"),
});

export function ModelDialog({ open, onOpenChange, editing, providers }: any) {
  const form = useForm<z.infer<typeof modelSchema>>({
    resolver: zodResolver(modelSchema),
    defaultValues: { nickname: "", provider: "", model: "", params_json: "{}" },
  });

  useEffect(() => {
    if (editing) {
      form.reset({
        nickname: editing.nickname,
        provider: editing.data.provider,
        model: editing.data.model,
        params_json: JSON.stringify(editing.data.params || {}, null, 2),
      });
    } else {
      form.reset({ nickname: "", provider: "", model: "", params_json: "{}" });
    }
  }, [editing, form, open]);

  async function onSubmit(values: z.infer<typeof modelSchema>) {
    try {
      const { nickname, params_json, ...rest } = values;
      const payload = { ...rest, params: JSON.parse(params_json) };
      await saveModelAction(nickname, payload);
      toast.success("Model configuration saved");
      onOpenChange(false);
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader><DialogTitle>{editing ? "Edit Model" : "Add Model"}</DialogTitle></DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control} name="nickname" render={({ field }) => (
                <FormItem>
                  <FormLabel>Nickname</FormLabel>
                  <FormControl><Input {...field} disabled={!!editing} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="provider" render={({ field }) => (
                <FormItem>
                  <FormLabel>Provider</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl><SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger></FormControl>
                    <SelectContent>
                      {providers.map((p: string) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
            </div>
            <FormField control={form.control} name="model" render={({ field }) => (
              <FormItem>
                <FormLabel>LiteLLM Model String</FormLabel>
                <FormControl><Input {...field} placeholder="openai/gpt-4" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="params_json" render={({ field }) => (
              <FormItem>
                <FormLabel>Model Parameters (JSON)</FormLabel>
                <FormControl><Textarea {...field} className="font-mono text-xs h-32" /></FormControl>
                <FormDescription>Temperature, max_tokens, etc.</FormDescription>
                <FormMessage />
              </FormItem>
            )} />
            <DialogFooter><Button type="submit">Save Configuration</Button></DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
