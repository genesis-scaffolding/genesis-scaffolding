'use server';

import { getAccessToken } from '@/lib/session';
import type { WorkflowManifest } from '@/types/workflow';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

/**
 * Fetches all available workflow manifests from the FastAPI backend.
 */
export async function getWorkflowsAction(): Promise<WorkflowManifest[]> {
  const token = await getAccessToken();

  if (!token) throw new Error('Unauthorized');

  try {
    const response = await fetch(`${FASTAPI_URL}/workflows`, {
      headers: { 'Authorization': `Bearer ${token}` },
      next: { revalidate: 60 }
    });

    if (!response.ok) throw new Error('Failed to fetch workflows');

    // The backend returns Record<string, WorkflowManifest>
    const data: Record<string, Omit<WorkflowManifest, 'id'>> = await response.json();

    // Map the object keys to an array and inject the key as 'id'
    return Object.entries(data).map(([id, manifest]) => ({
      ...manifest,
      id,
    })) as WorkflowManifest[];

  } catch (error) {
    console.error('[getWorkflowsAction] Error:', error);
    return [];
  }
}

/**
 * Fetches a single workflow manifest by its ID.
 */
export async function getWorkflowByIdAction(id: string): Promise<WorkflowManifest> {
  const token = await getAccessToken();

  const response = await fetch(`${FASTAPI_URL}/workflows/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    next: { revalidate: 60 }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch workflow: ${id}`);
  }

  const data = await response.json();

  // Inject the ID manually so the frontend components have it
  return {
    ...data,
    id,
  } as WorkflowManifest;
}
