import { getFilesAction, getFoldersAction } from '@/app/actions/sandbox';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';
import { SandboxFileExplorer } from '@/components/dashboard/sandbox-file-explorer';
import { HardDrive } from 'lucide-react';
import { Breadcrumb, BreadcrumbItem } from '@/components/dashboard/sandbox/breadcrumb';

interface SandboxPageProps {
  searchParams: Promise<{ folder?: string }>;
}

export default async function SandboxPage({ searchParams }: SandboxPageProps) {
  const { folder } = await searchParams;
  const [files, folders] = await Promise.all([getFilesAction(), getFoldersAction()]);

  // Build breadcrumb items
  const breadcrumbItems: BreadcrumbItem[] = [
    { label: 'sandbox', href: '/dashboard/sandbox' },
  ];
  if (folder) {
    const parts = folder.split('/');
    let accumulated = '';
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      accumulated = accumulated ? `${accumulated}/${part}` : part;
      const isLast = i === parts.length - 1;
      breadcrumbItems.push({
        label: part,
        href: isLast ? undefined : `/dashboard/sandbox?folder=${accumulated}`,
      });
    }
  }

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

        {breadcrumbItems.length > 1 && (
          <div className="bg-white rounded-xl border shadow-sm p-3">
            <Breadcrumb items={breadcrumbItems} />
          </div>
        )}

        <SandboxFileExplorer allFiles={files} allFolders={folders} folder={folder} />
      </PageBody>
    </PageContainer>
  );
}
