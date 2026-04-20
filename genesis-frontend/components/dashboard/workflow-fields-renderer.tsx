'use client';

import { Control } from 'react-hook-form';
import { WorkflowManifest } from '@/types/workflow';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { SandboxFilePicker } from '@/components/dashboard/sandbox-file-picker';
import { SandboxMultiFilePicker } from '@/components/dashboard/sandbox-multi-file-picker';

// Heuristic function to guess whether a string input field requires input or textarea
const isLongTextField = (key: string) => {
  const longTextKeywords = ['prompt', 'description', 'instruction', 'content', 'text', 'query', 'body', 'markdown', 'summary'];
  return longTextKeywords.some(keyword => key.toLowerCase().includes(keyword));
};

interface WorkflowFieldsRendererProps {
  workflow: WorkflowManifest;
  control: Control<any>;
  namePrefix?: string; // Optional prefix (e.g. "inputs.") for nested forms
  disabled?: boolean;
}

export function WorkflowFieldsRenderer({
  workflow,
  control,
  namePrefix = '',
  disabled = false
}: WorkflowFieldsRendererProps) {

  return (
    <>
      {Object.entries(workflow.inputs).map(([key, config]) => {
        // Construct the full path name (e.g. "inputs.my_param")
        const fieldName = `${namePrefix}${key}`;

        return (
          <FormField
            key={fieldName}
            control={control}
            name={fieldName}
            render={({ field }) => (
              <FormItem className="bg-white p-4 rounded-lg border shadow-sm">
                <FormLabel className="text-base font-semibold capitalize">
                  {key.replace(/_/g, ' ')}
                </FormLabel>
                <FormControl>
                  {(() => {
                    switch (config.type) {
                      case 'file':
                        return (
                          <SandboxFilePicker
                            value={field.value}
                            onChange={field.onChange}
                            placeholder={config.description}
                          />
                        );
                      case 'list[file]':
                        return (
                          <SandboxMultiFilePicker
                            value={field.value || []}
                            onChange={field.onChange}
                            placeholder={config.description}
                          />
                        );
                      case 'bool':
                        return (
                          <div className="flex items-center space-x-2 pt-2">
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                              disabled={disabled}
                            />
                            <span className="text-sm text-muted-foreground">Enable this option</span>
                          </div>
                        );
                      case 'int':
                      case 'float':
                        return (
                          <Input
                            type="number"
                            {...field}
                            disabled={disabled}
                            // Handle number conversion
                            onChange={(e) => field.onChange(config.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value))}
                          />
                        );
                      case 'string':
                      default:
                        if (isLongTextField(key)) {
                          return (
                            <Textarea
                              placeholder={config.description}
                              className="min-h-[120px] resize-y"
                              {...field}
                              disabled={disabled}
                              value={field.value ?? ''} // Fix for uncontrolled input warning
                            />
                          );
                        }
                        return (
                          <Input
                            placeholder={config.description}
                            {...field}
                            disabled={disabled}
                            value={field.value ?? ''} // Fix for uncontrolled input warning
                          />
                        );
                    }
                  })()}
                </FormControl>
                <FormDescription>{config.description}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        );
      })}
    </>
  );
}
