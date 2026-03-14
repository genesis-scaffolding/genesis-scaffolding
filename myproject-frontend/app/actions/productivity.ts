'use server'

import { apiFetch } from "@/lib/api-client";
import { revalidatePath } from "next/cache";
import { Task, Project, JournalEntry, JournalType } from "@/types/productivity";

// --- Tasks ---

export async function getTasksAction(params?: any): Promise<Task[]> {
  const query = new URLSearchParams(params).toString();
  const res = await apiFetch(`/productivity/tasks?${query}`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTaskAction(data: any) {
  const res = await apiFetch(`/productivity/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/productivity');
  return res.json();
}

export async function bulkUpdateTasksAction(data: {
  ids: number[],
  updates: any,
  add_project_ids?: number[],
  remove_project_ids?: number[]
}) {
  // Ensure we don't send undefined fields that might trigger validation errors
  const payload = {
    ids: data.ids,
    updates: data.updates,
    add_project_ids: data.add_project_ids || [],
    remove_project_ids: data.remove_project_ids || []
  };

  const res = await apiFetch(`/productivity/tasks/bulk`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json();
    console.error("Bulk Update Failed:", errorData);
    throw new Error("Failed to bulk update tasks");
  }

  revalidatePath('/dashboard/tasks');
  revalidatePath('/dashboard/projects');
  return res.json();
}

export async function getTaskAction(id: string | number): Promise<Task> {
  const res = await apiFetch(`/productivity/tasks/${id}`);
  if (!res.ok) throw new Error("Failed to fetch task");
  return res.json();
}

export async function updateTaskAction(id: number, data: any) {
  // We wrap the single ID into a list and use the bulk endpoint
  const payload = {
    ids: [id],
    updates: {
      title: data.title,
      description: data.description,
      status: data.status,
      assigned_date: data.assigned_date,
      hard_deadline: data.hard_deadline,
    },
    set_project_ids: data.project_ids, // Pass the new project list here
  };

  const res = await apiFetch(`/productivity/tasks/bulk`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });

  revalidatePath('/dashboard/tasks');
  revalidatePath(`/dashboard/tasks/${id}`);
  return res.json();
}

export async function deleteTaskAction(id: string | number) {
  const res = await apiFetch(`/productivity/tasks/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) throw new Error("Failed to delete task");

  revalidatePath('/dashboard/projects');
  revalidatePath('/dashboard/tasks');
}

// --- Projects ---

export async function getProjectsAction(): Promise<Project[]> {
  const res = await apiFetch(`/productivity/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function createProjectAction(data: any) {
  const res = await apiFetch(`/productivity/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/productivity');
  return res.json();
}

export async function getProjectAction(id: string | number): Promise<Project> {
  const res = await apiFetch(`/productivity/projects/${id}`);
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json();
}

export async function updateProjectAction(id: string | number, data: any) {
  const res = await apiFetch(`/productivity/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/projects');
  revalidatePath(`/dashboard/projects/${id}`);
  return res.json();
}

export async function deleteProjectAction(id: string | number) {
  const res = await apiFetch(`/productivity/projects/${id}`, {
    method: 'DELETE',
  });
  revalidatePath('/dashboard/projects');
}

// --- Journals ---

export async function getJournalsAction(params?: any): Promise<JournalEntry[]> {
  const query = new URLSearchParams(params).toString();
  const res = await apiFetch(`/productivity/journals?${query}`);
  if (!res.ok) throw new Error("Failed to fetch journals");
  return res.json();
}

export async function getJournalAction(id: string | number): Promise<JournalEntry> {
  const res = await apiFetch(`/productivity/journals/${id}`);
  if (!res.ok) throw new Error("Failed to fetch journal entry");
  return res.json();
}

export async function createJournalAction(data: any) {
  const res = await apiFetch(`/productivity/journals`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/journals');
  return res.json();
}

export async function updateJournalAction(id: string | number, data: any) {
  const res = await apiFetch(`/productivity/journals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  revalidatePath('/dashboard/journals');
  revalidatePath(`/dashboard/journals/${id}`);
  return res.json();
}

export async function findOrCreateJournalAction(data: {
  entry_type: JournalType;
  reference_date: string;
  title?: string;
}) {
  // 1. Check if it exists
  const entries = await getJournalsAction({
    entry_type: data.entry_type,
    reference_date: data.reference_date
  });

  if (entries.length > 0) {
    return entries[0]; // Return the existing one
  }

  // 2. Otherwise create it
  return await createJournalAction({
    ...data,
    content: "", // Start with empty content
  });
}


