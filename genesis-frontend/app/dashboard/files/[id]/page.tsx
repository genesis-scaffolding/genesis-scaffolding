import { getFileAction } from "@/app/actions/sandbox";
import { notFound } from "next/navigation";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Breadcrumb } from "@/components/dashboard/sandbox/breadcrumb";
import { FileViewer } from "@/components/dashboard/sandbox/file-viewer";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { decodeFileId } from "@/types/sandbox";
import { buildSandboxBreadcrumbs } from "@/components/dashboard/sandbox/breadcrumbs";

interface FileViewerPageProps {
  params: Promise<{ id: string }>;
}

export default async function FileViewerPage({ params }: FileViewerPageProps) {
  const { id } = await params;
  let relativePath: string;
  try {
    relativePath = decodeFileId(id);
  } catch {
    notFound();
  }

  let data;
  try {
    data = await getFileAction(relativePath);
  } catch {
    notFound();
  }

  const { file } = data;

  // Build path parts for back link and breadcrumb
  const pathParts = file.relative_path.split("/");
  pathParts.pop(); // Remove filename

  const breadcrumbItems = buildSandboxBreadcrumbs('/dashboard/files', file.relative_path);

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex flex-col gap-4">
          {/* Back link and breadcrumb */}
          <Breadcrumb items={breadcrumbItems} />

          {/* File viewer */}
          <FileViewer relativePath={relativePath} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
