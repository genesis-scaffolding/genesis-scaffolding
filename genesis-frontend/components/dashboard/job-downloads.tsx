import { FileText, Download, HardDrive } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JobFile } from "@/types/job";

export function JobDownloads({ jobId, files }: { jobId: number, files: JobFile[] }) {
  if (files.length === 0) return null;

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <HardDrive className="h-4 w-4" />
          Output Files
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {files.map((file) => (
          <div key={file.path} className="flex items-center justify-between p-3 rounded-lg border bg-white hover:bg-slate-50 transition-colors">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="p-2 bg-blue-50 rounded text-blue-600">
                <FileText className="h-4 w-4" />
              </div>
              <div className="flex flex-col overflow-hidden">
                <span className="text-sm font-medium truncate">{file.name}</span>
                <span className="text-xs text-muted-foreground">{formatSize(file.size)}</span>
              </div>
            </div>
            <Button variant="ghost" size="sm" asChild>
              {/* We point to our internal Next.js proxy route.
      The proxy will forward this to: ${FASTAPI_URL}/jobs/${jobId}/output/download/${file.path}
  */}
              <a
                href={`/api/jobs/${jobId}/output/download/${file.path}`}
                download={file.name}
              >
                <Download className="h-4 w-4" />
              </a>
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
