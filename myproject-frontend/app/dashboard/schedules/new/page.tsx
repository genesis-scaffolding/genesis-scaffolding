import { getWorkflowsAction } from '@/app/actions/workflow';
import { ScheduleForm } from '@/components/dashboard/schedule-form';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Zap } from 'lucide-react';
import Link from 'next/link';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';

export const metadata = {
  title: 'New Schedule | Genesis Scaffolding',
};

export default async function NewSchedulePage({
  searchParams,
}: {
  searchParams: Promise<{ workflowId?: string }>;
}) {
  const { workflowId } = await searchParams;
  const manifests = await getWorkflowsAction();

  // Step 1: Selection View
  if (!workflowId) {
    return (
      <PageContainer variant='dashboard'>
        <PageBody>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/dashboard/schedules">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div className="space-y-1">
              <h1 className="text-3xl font-bold tracking-tight">Select Workflow</h1>
              <p className="text-muted-foreground">
                Choose which workflow you would like to automate.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {manifests.map((manifest) => (
              <Link
                key={manifest.id}
                href={`/dashboard/schedules/new?workflowId=${manifest.id}`}
              >
                <Card className="hover:border-primary transition-colors cursor-pointer h-full">
                  <CardHeader>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 bg-primary/10 rounded-lg text-primary">
                        <Zap className="h-5 w-5" />
                      </div>
                      <CardTitle className="text-lg">{manifest.name}</CardTitle>
                    </div>
                    <CardDescription className="line-clamp-2">
                      {manifest.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </PageBody>
      </PageContainer>
    );
  }

  // Step 2: Configuration View
  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/schedules/new">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight">Configure Schedule</h1>
            <p className="text-muted-foreground">
              Set up the frequency and inputs for your automation.
            </p>
          </div>
        </div>

        <ScheduleForm manifests={manifests} selectedWorkflowId={workflowId} />
      </PageBody>
    </PageContainer>
  );
}
