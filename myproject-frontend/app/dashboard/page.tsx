import { format, isSameWeek, isToday, parseISO } from 'date-fns';
import { getTasksAction, getProjectsAction } from '@/app/actions/productivity';
import { getAgentsAction } from '@/app/actions/chat';
import { getWorkflowsAction } from '@/app/actions/workflow';
import { getJobsAction } from '@/app/actions/job';
import { getSchedulesAction } from '@/app/actions/schedule';

import { PageContainer, PageBody } from '@/components/dashboard/page-container';
import { StartChatButton } from '@/components/dashboard/start-chat-button';
import { TaskTable } from '@/components/dashboard/tasks/task-table';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CalendarDays, Briefcase, Bot, Play, ChevronRight, Activity } from 'lucide-react';
import Link from 'next/link';

export default async function DashboardPage() {
  const [tasks, projects, allAgents, workflows, jobs, schedules] = await Promise.all([
    getTasksAction({ include_completed: false }),
    getProjectsAction(),
    getAgentsAction(),
    getWorkflowsAction(),
    getJobsAction(5),
    getSchedulesAction(),
  ]);

  // 1. FILTERING LOGIC
  const now = new Date();
  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const agendaTasks = tasks.filter(t => {
    // Only show active tasks
    if (t.status === 'completed' || t.status === 'canceled') return false;

    // A: Assigned for today or overdue (Floating Date: YYYY-MM-DD)
    const isAssignedCurrentOrPast = t.assigned_date && t.assigned_date <= todayStr;

    // B: Deadline this week (ISO String)
    const hasDeadlineThisWeek = t.hard_deadline && isSameWeek(parseISO(t.hard_deadline), now);

    // C: Scheduled appointment today (ISO String)
    const isScheduledToday = t.scheduled_start && isToday(parseISO(t.scheduled_start));

    return isAssignedCurrentOrPast || hasDeadlineThisWeek || isScheduledToday;
  }).slice(0, 20);

  // Only show interactive agents for the dashboard chat quick-links
  const interactiveAgents = allAgents.filter((agent) => agent.interactive);

  const activeProjects = projects.filter(p => p.status !== 'completed');
  const activeSchedules = schedules.filter(s => s.enabled).length;

  return (
    <PageContainer variant="dashboard">
      {/* Increase vertical gap to 10 to separate sections clearly */}
      <PageBody className="gap-10">

        {/* SECTION 1: PULSE METRICS */}
        <section className="grid gap-6 grid-cols-1 md:grid-cols-3">
          <Card className="bg-primary/5 border-primary/20 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-semibold text-primary">Daily Agenda</CardTitle>
              <CalendarDays className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{agendaTasks.length} Tasks</div>
              <p className="text-xs text-muted-foreground mt-1">Due today or overdue</p>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
              <Briefcase className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{activeProjects.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Projects currently in progress</p>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Assistant Pulse</CardTitle>
              <Activity className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight">{activeSchedules} Active</div>
              <p className="text-xs text-muted-foreground mt-1">Schedules running & System online</p>
            </CardContent>
          </Card>
        </section>

        {/* SECTION 2: COMMAND GRID */}
        {/* Increase gap to 8 for more breathing room between columns */}
        <div className="grid gap-8 grid-cols-1 lg:grid-cols-12">

          {/* LEFT: FOCUS AGENDA */}
          <section className="lg:col-span-8 flex flex-col gap-6">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-xl font-bold tracking-tight">Your Priority</h2>
              <Button variant="ghost" size="sm" asChild className="text-muted-foreground">
                <Link href="/dashboard/tasks">View Full Backlog <ChevronRight className="ml-1 h-4 w-4" /></Link>
              </Button>
            </div>
            <div className="min-h-0 pt-2">
              <TaskTable
                tasks={agendaTasks}
                projects={projects}
                variant="dashboard"
              />
            </div>
          </section>

          {/* RIGHT: INTERACTION & AUTOMATION */}
          <section className="lg:col-span-4 flex flex-col gap-12">

            {/* 1. ASSISTANTS WIDGET */}
            <div className="space-y-6">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-primary" />
                  <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Assistants</h2>
                </div>
                <Button variant="ghost" size="sm" asChild className="text-muted-foreground hover:text-primary">
                  <Link href="/dashboard/agents">Registry <ChevronRight className="ml-1 h-4 w-4" /></Link>
                </Button>
              </div>

              <div className="flex flex-col gap-3">
                {interactiveAgents.slice(0, 3).map((agent) => (
                  <div
                    key={agent.id}
                    className="group flex items-center justify-between p-4 rounded-xl border bg-card hover:border-primary/30 hover:shadow-md transition-all duration-200"
                  >
                    <div className="min-w-0 flex-1 mr-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-bold truncate text-slate-900 dark:text-white">{agent.name}</span>
                        <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                      </div>
                      <p className="text-xs text-muted-foreground truncate leading-relaxed">
                        {agent.description || "Personal AI Assistant"}
                      </p>
                    </div>

                    {/* Replaced generic button with your StartChatButton component */}
                    <div className="shrink-0">
                      <StartChatButton
                        agentId={agent.id}
                        agentName={agent.name}
                      />
                    </div>
                  </div>
                ))}

                {interactiveAgents.length === 0 && (
                  <div className="text-center py-8 border rounded-xl border-dashed bg-slate-50/50 dark:bg-slate-900/50">
                    <p className="text-xs text-muted-foreground font-medium">No agents found.</p>
                  </div>
                )}
              </div>
            </div>

            {/* 2. WORKFLOWS WIDGET */}
            <div className="space-y-6">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <Play className="h-5 w-5 text-primary" />
                  <h2 className="text-xl font-bold tracking-tight">Workflows</h2>
                </div>
                <Button variant="ghost" size="sm" asChild className="text-muted-foreground hover:text-primary">
                  <Link href="/dashboard/workflows">All Workflows <ChevronRight className="ml-1 h-4 w-4" /></Link>
                </Button>
              </div>

              <div className="grid gap-2">
                {workflows.slice(0, 4).map((wf) => (
                  <Link
                    key={wf.id}
                    href={`/dashboard/workflows/${wf.id}`}
                    className="flex items-center justify-between p-4 px-5 rounded-xl border bg-card hover:bg-accent hover:border-primary/30 transition-all group shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-2 rounded-full bg-blue-400 group-hover:bg-primary transition-colors" />
                      <span className="text-sm font-semibold tracking-tight">{wf.name}</span>
                    </div>
                    <ChevronRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                  </Link>
                ))}
              </div>
            </div>

          </section>
        </div>

        {/* SECTION 3: RECENT ACTIVITY */}
        <section className="space-y-6">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-muted-foreground" />
              <h2 className="text-xl font-bold tracking-tight">Recent Activity</h2>
            </div>
            <Button variant="ghost" size="sm" asChild className="text-muted-foreground">
              <Link href="/dashboard/activity">View Full History <ChevronRight className="ml-1 h-4 w-4" /></Link>
            </Button>
          </div>

          <Card className="shadow-sm border-none bg-slate-50/50 dark:bg-slate-900/50">
            <CardContent className="p-0">
              <div className="divide-y divide-border/50">
                {jobs.length > 0 ? (
                  jobs.slice(0, 5).map((job: any) => {
                    // Find the human-readable name if available in the workflows catalog
                    const workflowName = workflows.find(w => w.id === job.workflow_id)?.name || job.workflow_id;

                    return (
                      <div key={job.id} className="flex items-center justify-between p-4 px-6 hover:bg-accent/30 transition-colors first:rounded-t-xl last:rounded-b-xl">
                        <div className="flex flex-col gap-1">
                          <span className="text-sm font-semibold text-slate-900 dark:text-white">
                            {workflowName}
                          </span>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="capitalize">{job.status}</span>
                            <span>•</span>
                            <span>{format(parseISO(job.created_at), 'MMM d, h:mm a')}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className={`h-2 w-2 rounded-full ${job.status === 'completed' ? 'bg-green-500' :
                            job.status === 'running' ? 'bg-blue-500 animate-pulse' :
                              'bg-slate-300'
                            }`} />

                          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                            <Link href={`/dashboard/jobs/${job.id}`}>
                              <ChevronRight className="h-4 w-4" />
                            </Link>
                          </Button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-12 text-center">
                    <p className="text-sm text-muted-foreground font-medium">No recent activity found.</p>
                    <p className="text-xs text-muted-foreground">Your assistant's work will appear here.</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </section>

      </PageBody>
    </PageContainer>
  );
}
