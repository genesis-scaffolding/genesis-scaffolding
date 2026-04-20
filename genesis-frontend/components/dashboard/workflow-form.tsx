'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { generateZodSchema } from '@/lib/workflow-utils';
import { WorkflowManifest } from '@/types/workflow';
import { SandboxFile } from '@/types/sandbox';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Rocket, Loader2 } from 'lucide-react';
import { createJobAction } from '@/app/actions/job';
import { toast } from 'sonner';
import { SandboxFilePicker } from '@/components/dashboard/sandbox-file-picker';
import { SandboxMultiFilePicker } from '@/components/dashboard/sandbox-multi-file-picker';
import { WorkflowFieldsRenderer } from '@/components/dashboard/workflow-fields-renderer';

// Heuristic function to guess whether a string input field requires input or textarea
const isLongTextField = (key: string) => {
  const longTextKeywords = ['prompt', 'description', 'instruction', 'content', 'text', 'query', 'body', 'markdown', 'summary'];
  return longTextKeywords.some(keyword => key.toLowerCase().includes(keyword));
};


export function WorkflowForm({ workflow }: { workflow: WorkflowManifest }) {
  const schema = generateZodSchema(workflow);
  const [isPending, setIsPending] = useState(false);

  const form = useForm({
    // @ts-ignore - The schema is generated dynamically at runtime, 
    // which confuses the static analysis of the zodResolver type definition.
    resolver: zodResolver(schema),
    defaultValues: Object.fromEntries(
      Object.entries(workflow.inputs).map(([key, val]) => {
        if (val.type === 'list[file]') return [key, []];
        if (val.type === 'file') return [key, null]; // Use null, not ''
        return [key, val.default ?? ''];
      })
    ),
  });

  async function onSubmit(values: any) {
    setIsPending(true);

    // Create a copy to modify
    const processedValues = { ...values };

    // Transform file lists from Objects back to Paths for the Backend
    for (const [key, config] of Object.entries(workflow.inputs)) {
      if (config.type === 'list[file]' && Array.isArray(processedValues[key])) {
        processedValues[key] = processedValues[key].map((f: SandboxFile) => f.relative_path);
      }
      if (config.type === 'file' && typeof processedValues[key] === 'object') {
        processedValues[key] = processedValues[key].relative_path;
      }
    }

    try {
      await createJobAction(workflow.id, processedValues);
      toast.success("Job submitted!");
    } catch (error: any) {
      toast.error(error.message);
      setIsPending(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <WorkflowFieldsRenderer
          workflow={workflow}
          control={form.control}
          disabled={isPending}
        />
        <Button
          type="submit"
          size="lg"
          className="w-full md:w-auto min-w-[150px]"
          disabled={isPending}
        >
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Dispatching...
            </>
          ) : (
            <>
              <Rocket className="mr-2 h-4 w-4" />
              Execute Workflow
            </>
          )}
        </Button>
      </form>
    </Form>
  );
}
