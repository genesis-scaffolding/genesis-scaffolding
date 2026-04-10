import { getFileAction } from "@/app/actions/sandbox";
import { notFound } from "next/navigation";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Breadcrumb, BreadcrumbItem } from "@/components/dashboard/sandbox/breadcrumb";
import { FileViewer } from "@/components/dashboard/sandbox/file-viewer";
import { HardDrive, ArrowLeft } from "lucide-react";
import Link from "next/link";

interface FileViewerPageProps {
  params: Promise<{ id: string }>;
}

export default async function FileViewerPage({ params }: FileViewerPageProps) {
  const { id } = await params;
  const fileId = parseInt(id, 10);
  if (isNaN(fileId)) notFound();

  let data;
  try {
    data = await getFileAction(fileId);
  } catch {
    notFound();
  }

  const { file } = data;

  // Build breadcrumb items from file's relative_path
  // relative_path looks like "folder1/folder2/file.md"
  const pathParts = file.relative_path.split("/");
  const filename = pathParts.pop(); // remove filename from path

  const breadcrumbItems: BreadcrumbItem[] = [
    { label: "sandbox", href: "/dashboard/sandbox" },
  ];

  // Build up intermediate folders
  let accumulatedPath = "";
  for (const part of pathParts) {
    accumulatedPath = accumulatedPath ? `${accumulatedPath}/${part}` : part;
    breadcrumbItems.push({
      label: part,
      href: `/dashboard/sandbox?folder=${accumulatedPath}`,
    });
  }

  // Add filename as last (non-clickable) item
  breadcrumbItems.push({ label: filename || file.filename });

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex flex-col gap-4">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2">
            <Link
              href={`/dashboard/sandbox?folder=${pathParts.join("/")}`}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sandbox
            </Link>
          </div>
          <Breadcrumb items={breadcrumbItems} />

          {/* Page title */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <HardDrive className="h-8 w-8 text-primary" />
              File Viewer
            </h1>
          </div>

          {/* File viewer */}
          <FileViewer fileId={fileId} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
