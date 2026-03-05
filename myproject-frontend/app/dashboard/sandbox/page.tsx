import { getFilesAction } from '@/app/actions/sandbox';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';
import { SandboxFileExplorer } from '@/components/dashboard/sandbox-file-explorer';
import { HardDrive } from 'lucide-react';

export default async function SandboxPage() {
  const files = await getFilesAction();

  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <HardDrive className="h-8 w-8 text-primary" />
              My Sandbox
            </h1>
            <p className="text-muted-foreground">
              Manage your persistent files, research papers, and workflow outputs.
            </p>
          </div>
        </div>

        <SandboxFileExplorer initialFiles={files} />
      </PageBody>
    </PageContainer>
  );
}
