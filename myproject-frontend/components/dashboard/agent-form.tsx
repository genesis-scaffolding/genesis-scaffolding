'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Loader2, Save, Bot, Wrench, Settings2, Sparkles } from 'lucide-react';

import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { createAgentAction, updateAgentAction } from '@/app/actions/chat'; // Import update action
import { Agent } from '@/types/chat';

const agentSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  description: z.string().min(5, "Description is too short"),
  system_prompt: z.string().min(10, "System prompt is required"),
  interactive: z.boolean(),
  model_name: z.string(),
  allowed_tools_raw: z.string(),
  allowed_agents_raw: z.string(),
});

type AgentFormValues = z.infer<typeof agentSchema>;

interface AgentFormProps {
  initialData?: Agent; // Optional agent for edit mode
}

export function AgentForm({ initialData }: AgentFormProps) {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const isEditMode = !!initialData;

  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentSchema),
    defaultValues: {
      name: initialData?.name || '',
      description: initialData?.description || '',
      system_prompt: initialData?.system_prompt || '',
      interactive: initialData?.interactive ?? true,
      model_name: initialData?.model_name || '',
      allowed_tools_raw: initialData?.allowed_tools?.join(', ') || '',
      allowed_agents_raw: initialData?.allowed_agents?.join(', ') || '',
    },
  });

  async function onSubmit(values: AgentFormValues) {
    setIsPending(true);
    try {
      const payload = {
        name: values.name,
        description: values.description,
        system_prompt: values.system_prompt,
        interactive: values.interactive,
        model_name: values.model_name.trim() === '' ? null : values.model_name.trim(),
        allowed_tools: values.allowed_tools_raw
          ? values.allowed_tools_raw.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        allowed_agents: values.allowed_agents_raw
          ? values.allowed_agents_raw.split(',').map(s => s.trim()).filter(Boolean)
          : [],
      };

      if (isEditMode && initialData) {
        await updateAgentAction(initialData.id, payload);
        toast.success("Agent updated successfully!");
      } else {
        await createAgentAction(payload);
        toast.success("Agent created successfully!");
      }

      router.push('/dashboard/agents');
      router.refresh(); // Ensure the registry list updates
    } catch (error: any) {
      toast.error(error.message);
    } finally {
      setIsPending(false);
    }
  }


  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10 bg-white p-8 rounded-xl border shadow-sm">

        {/* Section 1: Identity */}
        <section className="space-y-6">
          <div className="flex items-center gap-2 text-slate-900">
            <Bot className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold">{isEditMode ? 'Edit Agent Identity' : 'Agent Identity'}</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Agent Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g. Research Assistant"
                      {...field}
                      disabled={isEditMode} // Backend AgentEdit schema doesn't support name changes
                    />
                  </FormControl>
                  {isEditMode && <FormDescription className="text-[10px]">Name cannot be changed after creation.</FormDescription>}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="model_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model ID</FormLabel>
                  <FormControl><Input placeholder="provider/model" {...field} /></FormControl>
                  <FormDescription className="text-[11px] leading-tight mt-1">
                    Defaults to system LLM if left empty.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Short Description</FormLabel>
                <FormControl><Input placeholder="Briefly describe the agent's purpose" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </section>

        <Separator />

        {/* Section 2: Brain (System Prompt) */}
        <section className="space-y-6">
          <div className="flex items-center gap-2 text-slate-900">
            <Sparkles className="h-5 w-5 text-amber-500" />
            <h2 className="text-lg font-semibold">System Instructions</h2>
          </div>

          <FormField
            control={form.control}
            name="system_prompt"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Textarea
                    placeholder="You are a helpful assistant that..."
                    className="min-h-[250px] font-mono text-sm bg-slate-50/50 focus:bg-white transition-colors"
                    {...field}
                  />
                </FormControl>
                <FormDescription>These instructions define the core logic and personality of your agent.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </section>

        <Separator />

        {/* Section 3: Capabilities */}
        <section className="space-y-6">
          <div className="flex items-center gap-2 text-slate-900">
            <Wrench className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold">Capabilities & Context</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <FormField
              control={form.control}
              name="allowed_tools_raw"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Allowed Tools</FormLabel>
                  <FormControl><Input placeholder="e.g. google_search, duckduckgo" {...field} /></FormControl>
                  <FormDescription className="text-[11px]">Comma-separated tool IDs</FormDescription>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="allowed_agents_raw"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Sub-Agents</FormLabel>
                  <FormControl><Input placeholder="e.g. coder, designer" {...field} /></FormControl>
                  <FormDescription className="text-[11px]">Comma-separated agent IDs</FormDescription>
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="interactive"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-xl border bg-slate-50/50 p-4">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Settings2 className="h-4 w-4 text-slate-500" />
                    <FormLabel className="text-base">Interactive Mode</FormLabel>
                  </div>
                  <FormDescription>Allow this agent to appear in your Chat Registry</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
        </section>

        <div className="flex justify-end pt-4">
          <Button type="submit" size="lg" className="px-12" disabled={isPending}>
            {isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {isEditMode ? 'Save Changes' : 'Create Agent'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
