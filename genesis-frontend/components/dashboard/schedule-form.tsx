'use client';

import { useState, useMemo, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { WorkflowManifest } from '@/types/workflow';
import { createScheduleAction } from '@/app/actions/schedule';
import { generateZodSchema } from '@/lib/workflow-utils';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';

import { Button } from '@/components/ui/button';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TimezoneSelect } from './timezone-select';
import { toast } from 'sonner';
import { WorkflowFieldsRenderer } from '@/components/dashboard/workflow-fields-renderer';
import { SandboxFile } from '@/types/sandbox';

type ScheduleFormValues = {
  name: string;
  cron_expression: string;
  timezone: string;
  inputs: Record<string, any>;
};

interface ScheduleFormProps {
  manifests: WorkflowManifest[];
  selectedWorkflowId: string;
}

export function ScheduleForm({ manifests, selectedWorkflowId }: ScheduleFormProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedManifest = manifests.find(m => m.id === selectedWorkflowId);

  // 1. Memoize Schema
  const formSchema = useMemo(() => {
    const workflowSchema = selectedManifest
      ? generateZodSchema(selectedManifest)
      : z.any();

    return z.object({
      name: z.string().min(1, "Name is required"),
      cron_expression: z.string().min(1, "Cron expression is required"),
      timezone: z.string().min(1, "Timezone is required"),
      inputs: workflowSchema
    });
  }, [selectedManifest]);

  // 2. Calculate Default Values for Dynamic Inputs
  // This prevents the "Uncontrolled to Controlled" error
  const defaultInputs = useMemo(() => {
    if (!selectedManifest) return {};
    return Object.fromEntries(
      Object.entries(selectedManifest.inputs).map(([key, val]) => {
        if (val.type === 'list[file]') return [key, []];
        if (val.type === 'file') return [key, null];
        return [key, val.default ?? ''];
      })
    );
  }, [selectedManifest]);

  const form = useForm<ScheduleFormValues>({
    // @ts-ignore
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      cron_expression: '0 9 * * *',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      inputs: defaultInputs // Inject safe defaults
    }
  });

  // Reset form inputs when workflow changes to ensure defaults are applied
  useEffect(() => {
    if (selectedManifest) {
      form.reset({
        ...form.getValues(),
        inputs: defaultInputs
      });
    }
  }, [selectedManifest, defaultInputs, form]);

  async function onSubmit(values: ScheduleFormValues) {
    if (!selectedManifest) return;
    setIsSubmitting(true);

    // Process file inputs: Convert from UI Objects to Path Strings
    const processedInputs = { ...values.inputs };
    for (const [key, config] of Object.entries(selectedManifest.inputs)) {
      if (config.type === 'list[file]' && Array.isArray(processedInputs[key])) {
        processedInputs[key] = processedInputs[key].map((f: SandboxFile) => f.relative_path);
      }
      if (config.type === 'file' && processedInputs[key] && typeof processedInputs[key] === 'object') {
        processedInputs[key] = (processedInputs[key] as SandboxFile).relative_path;
      }
    }

    try {
      await createScheduleAction({
        name: values.name,
        workflow_id: selectedWorkflowId,
        cron_expression: values.cron_expression,
        timezone: values.timezone,
        inputs: processedInputs, // Send processed inputs
        enabled: true,
      });
      toast.success("Schedule created successfully");
      router.push('/dashboard/schedules');
    } catch (error: any) {
      toast.error(error.message || "Failed to create schedule");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!selectedManifest) return <div>Workflow not found.</div>;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="md:col-span-1 h-fit">
            <CardHeader>
              <CardTitle>Schedule Settings</CardTitle>
              <CardDescription>Define when this workflow should run.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Schedule Name</FormLabel>
                    <FormControl><Input placeholder="Daily Repo Audit" {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="cron_expression"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cron Expression</FormLabel>
                    <FormControl><Input placeholder="0 9 * * *" {...field} /></FormControl>
                    <FormDescription>
                      Use crontab format. <a href="https://crontab.guru" target="_blank" className="underline">crontab.guru</a>
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timezone</FormLabel>
                    <FormControl>
                      <TimezoneSelect value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Workflow Inputs</CardTitle>
              <CardDescription>Configuration for {selectedManifest.name}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Use the Reusable Renderer */}
              <WorkflowFieldsRenderer
                workflow={selectedManifest}
                control={form.control}
                namePrefix="inputs." // IMPORTANT: Nest inputs under "inputs"
                disabled={isSubmitting}
              />

              <div className="mt-8 flex justify-end">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Saving Schedule..." : "Save Schedule"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </Form>
  );
}
