import { getTasksAction, getProjectsAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { QuickAddTask } from "@/components/dashboard/tasks/quick-add-task";
import { TaskTable } from "@/components/dashboard/tasks/task-table";

export default async function TasksPage() {
  const [tasks, projects] = await Promise.all([
    getTasksAction({ include_completed: false }),
    getProjectsAction(),
  ]);

  return (
    <PageContainer variant="dashboard" hasFloatingActionMenu={false}>
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
