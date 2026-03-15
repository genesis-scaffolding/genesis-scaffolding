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
  set_project_ids?: number[]
}) {
  // Construct the payload dynamically
  const payload: any = {
    ids: data.ids,
    updates: data.updates,
  };

  // Only add these fields to the JSON body if they were actually passed in
  if (data.add_project_ids) payload.add_project_ids = data.add_project_ids;
  if (data.remove_project_ids) payload.remove_project_ids = data.remove_project_ids;
  if (data.set_project_ids) payload.set_project_ids = data.set_project_ids;

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
  project_id?: number;
  title?: string;
}) {
  // 1. Define uniqueness criteria
  const isPeriodic = ["daily", "weekly", "monthly", "yearly"].includes(data.entry_type);
  const isProject = data.entry_type === "project";

  // 2. Logic for finding existing entries
  let existingEntry = null;

  if (isPeriodic) {
    // Periodic notes are 1:1 with the date
    const entries = await getJournalsAction({
      entry_type: data.entry_type,
      reference_date: data.reference_date,
    });
    if (entries.length > 0) existingEntry = entries[0];
  }
  else if (isProject && data.project_id) {
    // Project notes are 1:1 with Project + Date + (Optional) Title
    // If you want to allow multiple DIFFERENT notes for the same project on the same day,
    // we should also check if the title matches.
    const entries = await getJournalsAction({
      entry_type: "project",
      reference_date: data.reference_date,
      project_id: data.project_id,
    });

    // If a title is provided, try to find a note with that exact title
    if (data.title) {
      existingEntry = entries.find(e => e.title === data.title);
    } else {
      // If no title provided, return the first "Untitled" project note for today
      existingEntry = entries.find(e => !e.title || e.title === "Untitled");
    }
  }

  // 3. If we found a match based on the logic above, return it
  if (existingEntry) {
    return existingEntry;
  }

  // 4. Otherwise (or if entry_type is 'general'), create a new one
  return await createJournalAction({
    ...data,
    content: "",
  });
}
