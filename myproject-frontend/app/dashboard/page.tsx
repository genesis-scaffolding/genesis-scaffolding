import Link from 'next/link';
import {
  Play,
  FileText,
  Clock,
  CheckCircle2,
  Layers,
  Calendar,
  ChevronRight
} from 'lucide-react';

import { getJobsAction } from '@/app/actions/job';
import { getFilesAction } from '@/app/actions/sandbox';
import { getSchedulesAction } from '@/app/actions/schedule';
import { getWorkflowsAction } from '@/app/actions/workflow';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PageContainer } from '@/components/dashboard/page-container'; // [NEW]

const StatusBadge = ({ status }: { status: string }) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Success</Badge>;
    case 'running':
      return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse">Running</Badge>;
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
};

export default async function DashboardPage() {
  const [jobs, files, schedules, workflows] = await Promise.all([
    getJobsAction(5),
    getFilesAction(),
    getSchedulesAction(),
    getWorkflowsAction(),
  ]);

  const activeSchedules = schedules.filter((s: any) => s.enabled).length;

  return (
    <PageContainer variant="dashboard">
      {/* We wrap content in a div to apply the vertical spacing between sections */}
      <div className="flex flex-col gap-8">

        {/* HEADER SECTION */}
        <section>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back. Here is what is happening with your AI assistant.</p>
        </section>

        {/* TOP ROW: PULSE METRICS */}
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Files</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{files.length}</div>
              <p className="text-xs text-muted-foreground">Files in sandbox storage</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Schedules</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{activeSchedules} / {schedules.length}</div>
              <p className="text-xs text-muted-foreground">Automated workflows enabled</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Available Workflows</CardTitle>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{workflows.length}</div>
              <p className="text-xs text-muted-foreground">Tools ready to dispatch</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Health</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">Connected</div>
              <p className="text-xs text-muted-foreground">FastAPI backend online</p>
            </CardContent>
          </Card>
        </section>

        {/* MAIN CONTENT AREA */}
        <section className="grid gap-4 md:grid-cols-7">
          {/* RECENT ACTIVITY */}
          <Card className="col-span-full md:col-span-4">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>The latest jobs executed by you or your schedules.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {jobs.length === 0 ? (
                  <div className="text-center py-10 text-muted-foreground text-sm">No jobs found.</div>
                ) : (
                  jobs.map((job: any) => (
                    <div key={job.id} className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0">
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-none">{job.workflow_id}</p>
                        <div className="flex items-center text-xs text-muted-foreground">
                          <Clock className="mr-1 h-3 w-3" />
                          {new Date(job.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <StatusBadge status={job.status} />
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/dashboard/jobs/${job.id}`}>
                            <ChevronRight className="h-4 w-4" />
                          </Link>
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
              {jobs.length > 0 && (
                <Button variant="outline" className="w-full mt-6" asChild>
                  <Link href="/dashboard/jobs">View All History</Link>
                </Button>
              )}
            </CardContent>
          </Card>

          {/* QUICK START */}
          <Card className="col-span-full md:col-span-3">
            <CardHeader>
              <CardTitle>Quick Start</CardTitle>
              <CardDescription>Trigger your most common tasks immediately.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {workflows.slice(0, 4).map((wf: any) => (
                <Link
                  key={wf.id}
                  href={`/dashboard/workflows/${wf.id}`}
                  className="group flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      <Play className="h-4 w-4 fill-current" />
                    </div>
                    <div className="text-sm font-medium">{wf.name}</div>
                  </div>
                  <ChevronRight className="h-4 w-4 opacity-50 group-hover:opacity-100" />
                </Link>
              ))}
              <Button variant="link" className="w-full text-muted-foreground text-xs" asChild>
                <Link href="/dashboard/workflows">See all workflows</Link>
              </Button>
            </CardContent>
          </Card>
        </section>

      </div>
    </PageContainer>
  );
}
