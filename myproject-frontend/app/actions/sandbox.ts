'use server';

import { getAccessToken } from '@/lib/session';
import { SandboxFile, TEXT_EXTENSIONS } from '@/types/sandbox';
import { revalidateTag } from 'next/cache';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

/**
 * Fetch all files in the user's sandbox
 */
export async function getFilesAction(): Promise<SandboxFile[]> {
  const token = await getAccessToken();
  const response = await fetch(`${FASTAPI_URL}/files/`, {
    headers: { 'Authorization': `Bearer ${token}` },
    next: { tags: ['sandbox'] } // Use tags for easy revalidation after upload
  });

  if (!response.ok) throw new Error('Failed to fetch sandbox files');
  return response.json();
}

/**
 * Upload a file to the sandbox
 */
export async function uploadFileAction(formData: FormData): Promise<SandboxFile> {
  const token = await getAccessToken();
  const subfolder = formData.get('subfolder') as string;

  const url = new URL(`${FASTAPI_URL}/files/upload`);
  if (subfolder) url.searchParams.append('subfolder', subfolder);

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData, // Send raw FormData (browser/Next.js handles boundary)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  const result = await response.json();
  const fileObject = result.file || result;

  if (!fileObject.id) {
    console.error("Backend did not return a file ID:", result);
    throw new Error("Upload succeeded but server did not return file metadata.");
  }
  // Refresh the sandbox data across the app
  revalidateTag('sandbox', "max");

  return fileObject as SandboxFile;
}


export async function deleteFileAction(fileId: number) {
  const token = await getAccessToken();

  const response = await fetch(`${FASTAPI_URL}/files/${fileId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete file');
  }

  revalidateTag('sandbox', "max");
  return { success: true };
}
/**
 * Fetch a single file's metadata and content by ID
 *
 * Note: The backend may not have a GET /files/{fileId}/content endpoint yet.
 * If it doesn't exist, the file viewer will show download-only for all files.
 */
export async function getFileAction(
  fileId: string | number
): Promise<{ file: SandboxFile; content?: string }> {
  const token = await getAccessToken();
  const id = typeof fileId === "string" ? parseInt(fileId, 10) : fileId;

  // Fetch metadata
  const metaResponse = await fetch(`${FASTAPI_URL}/files/${id}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!metaResponse.ok) {
    const errorData = await metaResponse.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch file metadata');
  }

  // Fetch content (text files only)
  // Note: GET /files/{fileId}/content endpoint may not exist on the backend yet.
  let content: string | undefined;
  const meta = await metaResponse.json();
  const ext = meta.filename.toLowerCase().slice(meta.filename.lastIndexOf('.'));
  const isTextFile =
    meta.mime_type?.startsWith('text/') ||
    ['text/plain', 'text/markdown', 'application/json'].includes(meta.mime_type) ||
    TEXT_EXTENSIONS.has(ext);

  if (isTextFile) {
    const contentResponse = await fetch(`${FASTAPI_URL}/files/${id}/content`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (contentResponse.ok) {
      content = await contentResponse.text();
    }
  }

  return { file: meta, content };
}

/**
 * Fetch available folders for organization
 */
export async function getFoldersAction(parentFolder?: string): Promise<string[]> {
  const token = await getAccessToken();
  const url = new URL(`${FASTAPI_URL}/files/folders`);
  if (parentFolder) url.searchParams.append('parent_folder', parentFolder);
  const response = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to fetch folders');
  return response.json();
}
