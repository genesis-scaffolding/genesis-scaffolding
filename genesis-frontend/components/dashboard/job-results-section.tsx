'use client';

import { useJob } from "./job-context";
import { JobDownloads } from "./job-downloads";
import { JobTextResults } from "./job-text-results";
import { Separator } from "@/components/ui/separator";
import { FileSearch, Hourglass } from "lucide-react";

interface JobResultsSectionProps {
  files: any[]; // Files are usually fetched in the page component
}

export function JobResultsSection({ files }: JobResultsSectionProps) {
  const { job } = useJob();

  if (job.status === 'completed') {
    return (
      <section className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-tight">Output & Results</h2>
          <span className="text-xs bg-muted px-2 py-1 rounded font-mono">
            {files.length} file(s) generated
          </span>
        </div>

        <div className="space-y-8">
          <JobDownloads jobId={job.id} files={files} />
          <Separator />
          <JobTextResults result={job.result} />
        </div>
      </section>
    );
  }

  if (job.status === 'failed') {
    return (
      <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed rounded-2xl bg-muted/30 text-muted-foreground text-center p-6">
        <FileSearch className="h-10 w-10 mb-4 opacity-20" />
        <h3 className="font-semibold text-foreground">Execution Failed</h3>
        <p className="text-sm max-w-xs">The workflow encountered an error. Check the status banner for details.</p>
      </div>
    );
  }

  // Pending or Running State
  return (
    <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed rounded-2xl text-muted-foreground text-center p-6 bg-muted/10">
      <Hourglass className="h-10 w-10 mb-4 animate-pulse opacity-20" />
      <h3 className="font-semibold">Processing Workflow</h3>
      <p className="text-sm max-w-xs">Results and files will automatically appear here once the job completes.</p>
    </div>
  );
}
