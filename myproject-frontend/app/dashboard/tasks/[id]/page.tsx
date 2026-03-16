import { getTaskAction, getProjectsAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Calendar,
  Clock,
  Flag,
  ArrowLeft,
  Edit3,
  Timer,
  CheckCircle2,
  Folder
} from "lucide-react";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import ReactMarkdown from 'react-markdown';

export default async function TaskDetailPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;

  // Fetch both task and projects to resolve names
  const [task, projects] = await Promise.all([
    getTaskAction(id),
    getProjectsAction()
  ]);

  const assignedProjects = projects.filter(p => task.project_ids.includes(p.id));

  const formatDuration = (mins?: number) => {
    if (!mins) return null;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  return (
    <PageContainer variant="dashboard">
      <PageBody className="pb-24">

        {/* Top Navigation */}
        <div className="mb-8 flex items-center justify-between">
          <Button variant="ghost" size="sm" asChild className="-ml-2">
            <Link href="/dashboard/tasks">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Tasks
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/dashboard/tasks/${task.id}/edit`}>
              <Edit3 className="mr-2 h-4 w-4" /> Edit Task
            </Link>
          </Button>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-start">

          {/* LEFT COLUMN: Main Content */}
          <div className="flex-1 space-y-8 w-full">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Badge variant={task.status === 'completed' ? 'secondary' : 'default'} className="capitalize px-3 py-1">
                  {task.status.replace('_', ' ')}
                </Badge>
              </div>
              <h1 className={`text-4xl md:text-5xl font-bold tracking-tight ${task.status === 'completed' ? 'line-through text-muted-foreground' : ''}`}>
                {task.title}
              </h1>
              {task.completed_at && (
                <div className="flex items-center text-green-600 dark:text-green-400 text-sm gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Completed on {format(new Date(task.completed_at), "PPP 'at' p")}</span>
                </div>
              )}
            </div>

            {/* Time Semantics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Planning */}
              <div className="p-4 rounded-xl border bg-card shadow-sm">
                <div className="flex items-center gap-2 text-muted-foreground mb-3">
                  <Calendar className="h-4 w-4" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">Planning</span>
                </div>
                <p className="text-sm font-medium text-muted-foreground">Assigned Date</p>
                <p className="text-base font-bold">
                  {task.assigned_date
                    ? format(parseISO(task.assigned_date), "EEEE, MMM d")
                    : "Not Planned"}
                </p>
              </div>

              {/* Appointment */}
              <div className="p-4 rounded-xl border bg-card shadow-sm">
                <div className="flex items-center gap-2 text-muted-foreground mb-3">
                  <Clock className="h-4 w-4" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">Appointment</span>
                </div>
                <p className="text-sm font-medium text-muted-foreground">Scheduled Start</p>
                <p className="text-base font-bold">
                  {task.scheduled_start
                    ? format(new Date(task.scheduled_start), "MMM d, h:mm a")
                    : "No Appointment"}
                </p>
                {task.duration_minutes && (
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-2 bg-muted/50 w-fit px-2 py-0.5 rounded-full">
                    <Timer className="h-3 w-3" />
                    <span>{formatDuration(task.duration_minutes)}</span>
                  </div>
                )}
              </div>

              {/* Constraint */}
              <div className="p-4 rounded-xl border bg-destructive/5 border-destructive/10">
                <div className="flex items-center gap-2 text-destructive mb-3">
                  <Flag className="h-4 w-4" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">Constraint</span>
                </div>
                <p className="text-sm font-medium text-muted-foreground">Hard Deadline</p>
                <p className="text-base font-bold text-destructive">
                  {task.hard_deadline
                    ? format(new Date(task.hard_deadline), "PPP")
                    : "No Deadline"}
                </p>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Description</h2>
              <div className="prose prose-blue dark:prose-invert max-w-none border rounded-2xl p-8 bg-card shadow-sm min-h-[300px]">
                {task.description ? (
                  <ReactMarkdown>{task.description}</ReactMarkdown>
                ) : (
                  <p className="text-muted-foreground italic">No description provided.</p>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: Sidebar Metadata */}
          <div className="w-full lg:w-80 shrink-0 space-y-6">
            <div className="border rounded-2xl p-6 bg-card shadow-sm space-y-6">
              <div>
                <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                  <Folder className="h-4 w-4 text-primary" /> Projects
                </h3>
                <div className="flex flex-wrap gap-2">
                  {assignedProjects.length > 0 ? (
                    assignedProjects.map(p => (
                      <Badge key={p.id} variant="secondary" className="font-normal">
                        {p.name}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No projects assigned</span>
                  )}
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Created</span>
                  <span>{format(new Date(task.created_at), "MMM d, yyyy")}</span>
                </div>
                {task.completed_at && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Finalized</span>
                    <span className="text-green-600 font-medium">Done</span>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Helper for Project Link */}
            {assignedProjects.length > 0 && (
              <div className="p-4 bg-primary/5 rounded-xl border border-primary/10">
                <p className="text-[10px] uppercase font-bold text-primary mb-2">Primary Project</p>
                <Link
                  href={`/dashboard/projects/${assignedProjects[0].id}`}
                  className="text-sm font-semibold hover:underline block truncate"
                >
                  View {assignedProjects[0].name} →
                </Link>
              </div>
            )}
          </div>

        </div>
      </PageBody>
    </PageContainer>
  );
}
