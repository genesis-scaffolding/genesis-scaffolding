'use client';

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Upload, Loader2 } from "lucide-react";
import { uploadFileAction } from '@/app/actions/sandbox';
import { toast } from "sonner";
import { SandboxFile } from '@/types/sandbox';

interface StandaloneUploadButtonProps {
  onSuccess?: (file: SandboxFile) => void;
}

export function StandaloneUploadButton({ onSuccess }: StandaloneUploadButtonProps) {
  const [uploading, setUploading] = useState(false);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const newFile = await uploadFileAction(formData);
      toast.success("Uploaded successfully");
      if (onSuccess) onSuccess(newFile);
    } catch (err: any) {
      toast.error(err.message || "Upload failed");
    } finally {
      setUploading(false);
      // Reset input so the same file can be uploaded again if needed
      e.target.value = '';
    }
  }

  return (
    <>
      <input
        type="file"
        accept=".pdf,.txt,.md"
        className="hidden"
        id="standalone-file-upload"
        onChange={handleFileUpload}
        disabled={uploading}
      />
      <Button asChild disabled={uploading}>
        <label htmlFor="standalone-file-upload" className="cursor-pointer gap-2">
          {uploading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Upload className="h-4 w-4" />
          )}
          {uploading ? "Uploading..." : "Upload New"}
        </label>
      </Button>
    </>
  );
}
