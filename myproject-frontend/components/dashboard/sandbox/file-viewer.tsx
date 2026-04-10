"use client";

import * as React from "react";
import { SandboxFile, TEXT_EXTENSIONS } from "@/types/sandbox";
import { getFileAction } from "@/app/actions/sandbox";
import { FileText, FileDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface FileViewerProps {
  fileId: string | number;
}

const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]);

function getFileType(filename: string): "text" | "image" | "pdf" | "unsupported" {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf("."));
  if (TEXT_EXTENSIONS.has(ext)) return "text";
  if (IMAGE_EXTS.has(ext)) return "image";
  if (ext === ".pdf") return "pdf";
  return "unsupported";
}

export function FileViewer({ fileId }: FileViewerProps) {
  const [data, setData] = React.useState<{ file: SandboxFile; content?: string } | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    getFileAction(fileId)
      .then(setData)
      .catch((err) => {
        setError(err.message || "Failed to load file");
        toast.error("Failed to load file");
      })
      .finally(() => setLoading(false));
  }, [fileId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "File not found"}</p>
        <Button onClick={() => window.open(`/api/files/${fileId}/download`, "_blank")}>
          <FileDown className="h-4 w-4 mr-2" /> Download
        </Button>
      </div>
    );
  }

  const { file, content } = data;
  const fileType = getFileType(file.filename);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-white rounded-xl border shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-500">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold">{file.filename}</h2>
            <p className="text-sm text-muted-foreground">
              {file.relative_path} · {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
        </div>
        <Button onClick={() => window.open(`/api/files/${fileId}/download`, "_blank")}>
          <FileDown className="h-4 w-4 mr-2" /> Download
        </Button>
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {fileType === "text" && content !== undefined && (
          <pre className="p-4 text-sm font-mono overflow-x-auto whitespace-pre-wrap break-words">
            {content}
          </pre>
        )}
        {fileType === "text" && content === undefined && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-muted-foreground">Preview not available for this file.</p>
            <Button onClick={() => window.open(`/api/files/${fileId}/download`, "_blank")}>
              <FileDown className="h-4 w-4 mr-2" /> Download to view
            </Button>
          </div>
        )}
        {fileType === "image" && (
          <div className="p-4 flex justify-center">
            <img
              src={`/api/files/${fileId}/download`}
              alt={file.filename}
              className="max-w-full h-auto rounded-lg"
            />
          </div>
        )}
        {fileType === "pdf" && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-muted-foreground">PDF preview not available in browser.</p>
            <Button onClick={() => window.open(`/api/files/${fileId}/download`, "_blank")}>
              <FileDown className="h-4 w-4 mr-2" /> Download to view
            </Button>
          </div>
        )}
        {fileType === "unsupported" && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-muted-foreground">Preview not available for this file type.</p>
            <Button onClick={() => window.open(`/api/files/${fileId}/download`, "_blank")}>
              <FileDown className="h-4 w-4 mr-2" /> Download
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
