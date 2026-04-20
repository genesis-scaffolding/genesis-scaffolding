'use client';

import React, { createContext, useContext, useEffect, useState, useTransition } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { forceRefreshAction } from '@/app/actions/refresh';
import { WorkflowJob } from '@/types/job';

interface JobContextType {
  job: WorkflowJob
  manifest: any;
  stepStates: Record<string, string>;
  isConnected: boolean;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

export function JobProvider({
  children,
  initialJob,
  manifest
}: {
  children: React.ReactNode;
  initialJob: WorkflowJob;
  manifest: any;
}) {
  const [job, setJob] = useState(initialJob);
  const [stepStates, setStepStates] = useState<Record<string, string>>(initialJob.step_status || {});
  const [isConnected, setIsConnected] = useState(false);

  const router = useRouter();
  const pathname = usePathname();
  const [_, startTransition] = useTransition();

  useEffect(() => {
    setJob(initialJob);
    setStepStates(initialJob.step_status || {});
  }, [initialJob]);

  useEffect(() => {
    // When user returns to the tab, sync with the DB immediately
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        startTransition(() => {
          router.refresh();
        });
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // If job is already finished, don't even open SSE
    if (job.status === 'completed' || job.status === 'failed') return;

    const eventSource = new EventSource(`/api/jobs/${job.id}/stream`);

    eventSource.onopen = () => setIsConnected(true);

    eventSource.addEventListener("step_start", (e: any) => {
      const data = JSON.parse(e.data);
      setStepStates(prev => ({ ...prev, [data.step_id]: 'running' }));
    });

    eventSource.addEventListener("step_completed", (e: any) => {
      const data = JSON.parse(e.data);
      setStepStates(prev => ({ ...prev, [data.step_id]: 'completed' }));
    });

    eventSource.addEventListener("step_failed", (e: any) => {
      const data = JSON.parse(e.data);
      setStepStates(prev => ({ ...prev, [data.step_id]: 'failed' }));
    });

    eventSource.addEventListener("status", (e: any) => {
      const newStatus = e.data.toLowerCase(); // 'completed' or 'failed'

      if (newStatus === 'completed' || newStatus === 'failed') {
        // Update local state immediately so the UI reacts 
        setJob(prev => ({ ...prev, status: newStatus }));
        setIsConnected(false);
        eventSource.close();

        // Trigger server-side refresh to get files/final results
        startTransition(async () => {
          await forceRefreshAction(pathname);
          router.refresh();
        });
      }
    });

    // Listen for custom "error" events from Python
    eventSource.addEventListener("error", (e: any) => {
      try {
        const data = JSON.parse(e.data);
        setJob(prev => ({ ...prev, error_message: data.message }));
      } catch (err) {
        console.error("Failed to parse SSE error message");
      }
    });

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
    };

    return () => eventSource.close();
  }, [job.id, job.status, pathname, router]);

  return (
    <JobContext.Provider value={{ job, manifest, stepStates, isConnected }}>
      {children}
    </JobContext.Provider>
  );
}

export const useJob = () => {
  const context = useContext(JobContext);
  if (!context) throw new Error("useJob must be used within a JobProvider");
  return context;
};
