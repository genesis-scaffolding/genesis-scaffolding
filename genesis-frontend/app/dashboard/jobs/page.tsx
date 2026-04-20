import { getJobsAction } from "@/app/actions/job";
import { JobsTable } from "@/components/dashboard/jobs/jobs-table";
import { Button } from "@/components/ui/button";
import { RefreshCcw } from "lucide-react";
import { revalidatePath } from "next/cache";
import { PageBody, PageContainer } from "@/components/dashboard/page-container";

export default async function JobsListPage() {
  const jobs = await getJobsAction();

  async function refresh() {
    'use server';
    revalidatePath('/dashboard/jobs');
  }

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Job History</h1>
            <p className="text-muted-foreground">
              Monitor and review your previous workflow executions.
            </p>
          </div>
          <form action={refresh}>
            <Button variant="outline" size="sm">
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </form>
        </div>
        <JobsTable jobs={jobs} />
      </PageBody>
    </PageContainer>
  );
}
