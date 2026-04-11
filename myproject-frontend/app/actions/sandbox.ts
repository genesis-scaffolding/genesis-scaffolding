'use server';

import { getAccessToken } from '@/lib/session';
import { SandboxFile, TEXT_EXTENSIONS, encodeFileId } from '@/types/sandbox';
import { revalidateTag } from 'next/cache';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

/**
 * Fetch all files in the user's sandbox
 * @param folder Folder to list files from. Defaults to "." (root)
 */
export async function getFilesAction(folder: string = "."): Promise<SandboxFile[]> {
  const token = await getAccessToken();
  const url = new URL(`${FASTAPI_URL}/files/`);
  if (folder && folder !== ".") url.searchParams.append('folder', folder);
  const response = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` },
    next: { tags: ['sandbox'] }
  });

  if (!response.ok) throw new Error('Failed to fetch sandbox files');
  const results = await response.json();
  // API returns FileUploadResponse objects: { message: string, file: SandboxFile }
  // Extract just the file from each response
  return results.map((r: { message: string; file: SandboxFile }) => r.file);
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
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  const result = await response.json();
  // Response is now { message: string, file: SandboxFile }
  const fileObject = result.file;

  if (!fileObject.relative_path) {
    console.error("Backend did not return a file relative_path:", result);
    throw new Error("Upload succeeded but server did not return file metadata.");
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (revalidateTag as any)('sandbox');

  return fileObject as SandboxFile;
}


/**
 * Delete a file by its relative path
 */
export async function deleteFileAction(relativePath: string) {
  const token = await getAccessToken();
  const encodedId = encodeFileId(relativePath);

  const response = await fetch(`${FASTAPI_URL}/files/${encodedId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete file');
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (revalidateTag as any)('sandbox');
  return { success: true };
}

/**
 * Move multiple files to a destination folder
 * @param sourcePaths Array of relative paths to move
 * @param destinationFolder Target folder path ("." for root)
 */
export async function moveFilesAction(sourcePaths: string[], destinationFolder: string) {
  const token = await getAccessToken();

  const response = await fetch(`${FASTAPI_URL}/files/move`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      source_paths: sourcePaths,
      destination_folder: destinationFolder,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to move files');
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (revalidateTag as any)('sandbox');
  return response.json();
}

/**
 * Create a new directory in the sandbox
 * @param relativePath Path for the new directory (e.g., "my_folder" or "docs/notes")
 */
export async function createFolderAction(relativePath: string): Promise<SandboxFile> {
  const token = await getAccessToken();

  const response = await fetch(`${FASTAPI_URL}/files/folders`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ relative_path: relativePath }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create folder');
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (revalidateTag as any)('sandbox');
  return response.json();
}

/**
 * Fetch a single file's metadata and content by relative path
 */
export async function getFileAction(
  relativePath: string
): Promise<{ file: SandboxFile; content?: string }> {
  const token = await getAccessToken();
  const encodedId = encodeFileId(relativePath);

  // Fetch metadata
  const metaResponse = await fetch(`${FASTAPI_URL}/files/${encodedId}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!metaResponse.ok) {
    const errorData = await metaResponse.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch file metadata');
  }

  // Fetch content (text files only)
  let content: string | undefined;
  const metaResult = await metaResponse.json();
  // API returns FileUploadResponse: { message: string, file: SandboxFile }
  const meta = metaResult.file || metaResult;
  const ext = meta.name.toLowerCase().slice(meta.name.lastIndexOf('.'));
  const isTextFile =
    meta.mime_type?.startsWith('text/') ||
    ['text/plain', 'text/markdown', 'application/json'].includes(meta.mime_type) ||
    TEXT_EXTENSIONS.has(ext);

  if (isTextFile) {
    const contentResponse = await fetch(`${FASTAPI_URL}/files/${encodedId}/content`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (contentResponse.ok) {
      const data = await contentResponse.json();
      content = data.content;
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
