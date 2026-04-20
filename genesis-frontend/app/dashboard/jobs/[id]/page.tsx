export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

import { getJobByIdAction, getJobFilesAction } from "@/app/actions/job";
import { getWorkflowByIdAction } from "@/app/actions/workflow";
import { notFound } from "next/navigation";
import { JobStatusBanner } from "@/components/dashboard/job-status-banner";
import { JobProvider } from "@/components/dashboard/job-context";
import { JobStepChecklist } from "@/components/dashboard/job-step-checklist";
import { JobResultsSection } from "@/components/dashboard/job-results-section";
import { PageBody, PageContainer } from "@/components/dashboard/page-container";
import { PageHeader } from "@/components/dashboard/page-header";



export default async function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const jobId = parseInt(id);

  try {
    const [job, files] = await Promise.all([
      getJobByIdAction(jobId),
      getJobFilesAction(jobId)
    ]);

    const manifest = await getWorkflowByIdAction(job.workflow_id)

    // This is an effort to fix the problem that the GUI does not update after SSE completes with some workflows
    // This forces React to destroy the old "Running" component tree and 
    // mount the new "Completed" one immediately.
    const pageKey = `${job.id}-${job.status}-${files.length}`;

    return (
      <PageContainer variant="dashboard">
        <PageBody>
          <PageHeader />
          <JobProvider initialJob={job} manifest={manifest}>
            <header>
              <h1 className="text-3xl font-bold tracking-tight">Execution Detail</h1>
              <p className="text-muted-foreground font-mono text-sm">Job ID: #{job.id}</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <aside className="space-y-6">
                {/* These components now internally use useJob() */}
                <JobStatusBanner />
                <JobStepChecklist />
              </aside>

              <main className="lg:col-span-2">
                <JobResultsSection files={files} />
              </main>
            </div>
          </JobProvider>
        </PageBody>
      </PageContainer>
    );
  } catch (error) {
    notFound();
  }
}
