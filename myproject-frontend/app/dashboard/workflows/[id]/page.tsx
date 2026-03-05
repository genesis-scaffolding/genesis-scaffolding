import { getWorkflowByIdAction } from '@/app/actions/workflow';
import { notFound } from 'next/navigation';
import { WorkflowForm } from '@/components/dashboard/workflow-form';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';

export default async function WorkflowExecutionPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;

  try {
    const workflow = await getWorkflowByIdAction(id);

    return (
      <PageContainer>
        <PageBody>
          <header className="space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-3xl font-bold tracking-tight">{workflow.name}</h1>
              <Badge variant="secondary">v{workflow.version}</Badge>
            </div>
            <p className="text-lg text-muted-foreground">{workflow.description}</p>
            <Separator />
          </header>

          <div className="grid gap-8">
            <section>
              <h2 className="text-xl font-semibold mb-4">Configuration</h2>
              <WorkflowForm workflow={workflow} />
            </section>
          </div>
        </PageBody>
      </PageContainer>
    );
  } catch (error) {
    console.log("CRITICAL ERROR IN WORKFLOW PAGE:", error);
    notFound()
  }
}
