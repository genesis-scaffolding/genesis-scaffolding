'use client';

import { useJob } from "./job-context";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function JobStepChecklist() {
  const { manifest, stepStates } = useJob();
  const steps = manifest?.steps || [];

  return (
    <div className="p-5 border rounded-xl bg-card shadow-sm">
      <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-6">
        Workflow Pipeline
      </h3>
      <div className="space-y-5">
        {steps.map((step: any, index: number) => {
          const status = stepStates[step.id] || 'pending';
          return (
            <div key={step.id} className="relative flex items-start gap-4">
              {/* Vertical line connecting steps */}
              {index !== steps.length - 1 && (
                <div className="absolute left-[9px] top-6 w-[2px] h-6 bg-muted" />
              )}

              <div className="relative z-10 bg-card">
                <StepIcon status={status} />
              </div>

              <div className="flex flex-col">
                <span className={cn(
                  "text-sm font-semibold transition-colors",
                  status === 'pending' && "text-muted-foreground",
                  status === 'running' && "text-blue-600",
                  status === 'completed' && "text-foreground",
                  status === 'failed' && "text-red-600"
                )}>
                  {step.id.replace(/_/g, ' ')}
                </span>
                <span className="text-[11px] text-muted-foreground italic">
                  {status === 'running' && 'In progress...'}
                  {status === 'completed' && 'Done'}
                  {status === 'failed' && 'Step failed'}
                  {status === 'pending' && 'Waiting...'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StepIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 className="h-5 w-5 text-green-500" />;
  if (status === 'running') return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
  return <Circle className="h-5 w-5 text-muted-foreground/30" />;
}
