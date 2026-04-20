import { getWorkflowsAction } from '@/app/actions/workflow';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';
import { WorkflowCard } from '@/components/dashboard/workflow-card';

export default async function CatalogPage() {
  const workflows = await getWorkflowsAction();

  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Workflow Catalog
          </h1>
          <p className="text-lg text-muted-foreground">
            Deploy an agentic workflow by selecting a template below.
          </p>
        </header>

        {workflows.length > 0 ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {workflows.map((workflow) => (
              <WorkflowCard key={workflow.id} workflow={workflow} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed rounded-xl bg-slate-50">
            <p className="text-muted-foreground font-medium">No workflows available</p>
            <p className="text-sm text-muted-foreground/70">Check your backend manifest directory.</p>
          </div>
        )}
      </PageBody>
    </PageContainer>
  );
}
