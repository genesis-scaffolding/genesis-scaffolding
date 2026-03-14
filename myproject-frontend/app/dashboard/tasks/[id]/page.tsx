import { getTaskAction, getProjectsAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Calendar, Clock, Edit3, ArrowLeft, Folder } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import ReactMarkdown from 'react-markdown';

export default async function TaskDetailPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;
  const task = await getTaskAction(id);
  const allProjects = await getProjectsAction();

  // Find the names of the projects this task belongs to
  const assignedProjects = allProjects.filter(p => task.project_ids.includes(p.id));

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <Button variant="ghost" size="sm" asChild className="-ml-2 mb-6">
          <Link href="/dashboard/tasks">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Tasks
          </Link>
        </Button>

        <div className="flex flex-col md:flex-row justify-between gap-6 items-start">
          <div className="flex-1 space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant={task.status === 'completed' ? 'secondary' : 'default'} className="capitalize">
                  {task.status.replace('_', ' ')}
                </Badge>
              </div>
              <h1 className={`text-4xl font-bold ${task.status === 'completed' ? 'line-through text-muted-foreground' : ''}`}>
                {task.title}
              </h1>
            </div>

            <div className="prose dark:prose-invert max-w-none border rounded-lg p-6 bg-muted/30">
              {task.description ? (
                <ReactMarkdown>{task.description}</ReactMarkdown>
              ) : (
                <p className="italic text-muted-foreground">No description provided.</p>
              )}
            </div>
          </div>

          <Card className="w-full md:w-80 shrink-0">
            <div className="p-6 space-y-6">
              <Button className="w-full" asChild>
                <Link href={`/dashboard/tasks/${task.id}/edit`}>
                  <Edit3 className="mr-2 h-4 w-4" /> Edit Task
                </Link>
              </Button>

              <div className="space-y-4 text-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center text-muted-foreground">
                    <Calendar className="mr-2 h-4 w-4" /> Hard Deadline
                  </div>
                  <span className="font-medium">{task.hard_deadline ? format(new Date(task.hard_deadline), "PPP") : "None"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center text-muted-foreground">
                    <Clock className="mr-2 h-4 w-4" /> Assigned
                  </div>
                  <span className="font-medium">{task.assigned_date || "Not scheduled"}</span>
                </div>
              </div>

              <Separator />

              <div>
                <p className="text-sm font-medium mb-3 flex items-center">
                  <Folder className="mr-2 h-4 w-4" /> Projects
                </p>
                <div className="flex flex-wrap gap-2">
                  {assignedProjects.length > 0 ? (
                    assignedProjects.map(p => (
                      <Badge key={p.id} variant="secondary">{p.name}</Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No projects assigned</span>
                  )}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </PageBody>
    </PageContainer>
  );
}

// Simple Card helper since we used it in the detail layout
function Card({ children, className }: { children: React.ReactNode, className?: string }) {
  return <div className={`border rounded-xl bg-card text-card-foreground shadow-sm ${className}`}>{children}</div>
}
