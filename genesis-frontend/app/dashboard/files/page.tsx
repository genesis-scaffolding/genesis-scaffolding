import { getFilesAction, getFoldersAction } from '@/app/actions/sandbox';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';
import { SandboxFileExplorer } from '@/components/dashboard/sandbox-file-explorer';
import { Breadcrumb } from '@/components/dashboard/sandbox/breadcrumb';
import { buildSandboxBreadcrumbs } from '@/components/dashboard/sandbox/breadcrumbs';

interface FilesPageProps {
  searchParams: Promise<{ folder?: string }>;
}

export default async function FilesPage({ searchParams }: FilesPageProps) {
  const { folder } = await searchParams;
  const [files, folders] = await Promise.all([
    getFilesAction(folder || "."),
    getFoldersAction(folder || ".")
  ]);

  const breadcrumbItems = buildSandboxBreadcrumbs('/dashboard/files', folder || '');

  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        {breadcrumbItems.length > 1 && (
          <Breadcrumb items={breadcrumbItems} />
        )}

        <SandboxFileExplorer allFiles={files} allFolders={folders} folder={folder} />
      </PageBody>
    </PageContainer>
  );
}
