'use client';

import { useEffect, useRef, useTransition, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { forceRefreshAction } from '@/app/actions/refresh';

interface JobRealtimeListenerProps {
  jobId: number;
  status: string; // Current status passed from the server component
  manifestSteps: { id: string }[]; // list of workflow steps
  initialStepStatus: Record<string, string>; // From job.step_status
}

export function JobRealtimeListener({ jobId,
  status,
  manifestSteps,
  initialStepStatus }: JobRealtimeListenerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const isTerminatingRef = useRef(false);
  const [stepStates, setStepStates] = useState<Record<string, string>>(initialStepStatus);

  useEffect(() => {
    // Helper to refresh Server Components
    // Add debounce to prevent "Step Completed" (Running) request from overwriting "Job Completed" (Done) request
    const triggerUpdate = async (isFinal = false) => {
      if (isTerminatingRef.current && !isFinal) return;

      // 1. Invalidate Server Cache via Action
      await forceRefreshAction(pathname);

      // 2. Trigger Client Refresh within a Transition
      // This tells React to prioritize this UI update
      startTransition(() => {
        router.refresh();
      });
    };

    // Stop conditions: If job is already done, do not open connection.
    // This is used when we open the job detail page and the job itself is already done or failed
    if (status === 'completed' || status === 'failed') {
      return;
    }

    // Connect to the Proxy
    // The proxy will route this to FastAPI: /jobs/{id}/stream
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    // Listen for FastAPI specific events
    // Based on WorkflowEventType enum defined in the core

    eventSource.onopen = () => {
      console.log(`[SSE] Connected to job ${jobId}`);
    };

    // Step updates
    eventSource.addEventListener("step_start", (e: any) => {
      const data = JSON.parse(e.data);
      setStepStates(prev => ({ ...prev, [data.step_id]: 'running' }));
    });

    eventSource.addEventListener("step_completed", (e: any) => {
      const data = JSON.parse(e.data);
      setStepStates(prev => ({ ...prev, [data.step_id]: 'completed' }));
    });

    // Logs: Optional 
    eventSource.addEventListener("log", () => {
      // For now, let's refresh to show the log in the UI
      triggerUpdate();
    });

    eventSource.addEventListener("error", (e) => {
      console.error("Job Error:", (e as MessageEvent).data);
      triggerUpdate();
    });

    // Handle Completion
    // Python code sends { "event": "status", "data": "COMPLETED" } 
    // to signal the loop to break. We catch that here.
    eventSource.addEventListener("status", (e) => {
      const newStatus = (e as MessageEvent).data;
      if (newStatus === 'COMPLETED' || newStatus === 'FAILED') {
        isTerminatingRef.current = true;
        eventSource.close();

        // Give the DB a final 500ms to settle then force the update
        setTimeout(() => {
          triggerUpdate(true);
        }, 500);
      }
    });

    // Cleanup
    eventSource.onerror = (err) => {
      console.error("SSE Error (closing connection):", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, status, router]);

  return null; // This component is invisible
}
