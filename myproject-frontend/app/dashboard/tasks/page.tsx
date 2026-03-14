import { getTasksAction, getProjectsAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { QuickAddTask } from "@/components/dashboard/tasks/quick-add-task";
import { TaskTable } from "@/components/dashboard/tasks/task-table"; // We'll build this next

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function TasksPage({ searchParams }: PageProps) {
  // Pass server-side sorting/filtering to the action
  const resolvedParams = await searchParams;
  const tasks = await getTasksAction(resolvedParams);
  const projects = await getProjectsAction();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
            <p className="text-muted-foreground">Your global backlog and scheduled work.</p>
          </div>

          <QuickAddTask />

          <TaskTable tasks={tasks} projects={projects} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
