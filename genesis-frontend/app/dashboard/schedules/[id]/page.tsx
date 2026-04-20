import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { getScheduleByIdAction } from '@/app/actions/schedule';
import { getJobsAction } from '@/app/actions/job';
import { JobsTable } from '@/components/dashboard/jobs-table';
import { formatRelativeTime } from '@/lib/date-utils';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';
import { PageHeader } from '@/components/dashboard/page-header';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ScheduleDetailsPage({ params }: PageProps) {
  const { id } = await params;
  const scheduleId = parseInt(id);

  // Parallel data fetching
  const [schedule, jobs] = await Promise.all([
    getScheduleByIdAction(scheduleId),
    getJobsAction(20, 0, scheduleId)
  ]);

  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        <PageHeader />
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{schedule.name}</h1>
              <Badge variant={schedule.enabled ? "default" : "secondary"}>
                {schedule.enabled ? "Active" : "Paused"}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-muted-foreground text-sm">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <code>{schedule.cron_expression}</code>
                <span>({schedule.timezone})</span>
              </div>
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Last Run: {formatRelativeTime(schedule.last_run_at)}
              </div>
            </div>
          </div>
        </div>

        {/* Inputs Summary (Optional) */}
        <div className="bg-muted/30 p-4 rounded-lg border">
          <h3 className="font-semibold mb-2 text-sm">Configured Inputs</h3>
          <pre className="text-xs bg-background p-2 rounded border overflow-auto max-h-[150px]">
            {JSON.stringify(schedule.inputs, null, 2)}
          </pre>
        </div>

        {/* Execution History */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold tracking-tight">Execution History</h2>
          {/* Pass the filtered jobs to your existing table component */}
          <JobsTable jobs={jobs} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
