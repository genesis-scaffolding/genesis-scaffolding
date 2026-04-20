import { getProjectAction, getProjectsAction, getTasksAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Edit3, ArrowLeft, Calendar } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { QuickAddTask } from "@/components/dashboard/tasks/quick-add-task";
import { PageHeader } from "@/components/dashboard/page-header";
import { TaskTable } from "@/components/dashboard/tasks/task-table";

export default async function ProjectDetailPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;

  const [project, tasks, projects] = await Promise.all([
    getProjectAction(id),
    getTasksAction({ project_id: id, include_completed: true }),
    getProjectsAction()
  ]);
  const completedTasks = tasks.filter(t => t.status?.toLowerCase().trim() === 'completed').length;
  const progress = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0;

  return (
    <PageContainer variant="dashboard">
      <PageBody className="pb-24">
        <div className="mb-6">
          <PageHeader>
            <Button variant="outline" asChild>
              <Link href={`/dashboard/projects/${project.id}/edit`}>
                <Edit3 className="mr-2 h-4 w-4" /> Edit Project
              </Link>
            </Button>
          </PageHeader>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold">{project.name}</h1>
                <Badge variant="outline" className="capitalize">{project.status}</Badge>
              </div>
              <p className="text-muted-foreground max-w-2xl">{project.description}</p>
            </div>

          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-4 mb-8">
          <div className="border rounded-lg p-4 bg-card">
            <p className="text-sm font-medium text-muted-foreground">Progress</p>
            <p className="text-2xl font-bold">{progress}%</p>
            <div className="w-full bg-secondary h-2 rounded-full mt-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="border rounded-lg p-4 bg-card">
            <p className="text-sm font-medium text-muted-foreground">Tasks</p>
            <p className="text-2xl font-bold">{tasks.length}</p>
          </div>
          <div className="border rounded-lg p-4 bg-card">
            <p className="text-sm font-medium text-muted-foreground">Open</p>
            <p className="text-2xl font-bold">{tasks.length - completedTasks}</p>
          </div>
          <div className="border rounded-lg p-4 bg-card">
            <p className="text-sm font-medium text-muted-foreground">Deadline</p>
            <div className="flex items-center gap-2 mt-1">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <p className="font-semibold">
                {project.deadline ? format(new Date(project.deadline), "MMM d") : "None"}
              </p>
            </div>
          </div>
        </div>

        <Separator className="my-8" />

        <div className="space-y-4 pb-24">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Project Tasks</h2>
          </div>

          {/* We pass project_id to the list so new tasks created here are automatically linked */}
          <TaskTable
            tasks={tasks}
            projects={projects}
            variant="list"
            floatingOffset={true}
          />
        </div>
        <div className="fixed bottom-6 left-0 right-0 px-4 md:left-[240px] z-50 pointer-events-none">
          <div className="max-w-4xl mx-auto pointer-events-auto">
            <div className="bg-background/80 backdrop-blur-md border rounded-xl shadow-2xl p-2 border-primary/20">
              <QuickAddTask defaultProjectId={Number(project.id)} />
            </div>
          </div>
        </div>
      </PageBody>
    </PageContainer>
  );
}
