'use server'

import { apiFetch } from "@/lib/api-client";
import { revalidatePath } from "next/cache";
import { EventLog, TopicalMemory, MemoryListResponse, TagCountResponse, MemoryRevisionChain } from "@/types/memory";

export async function getMemoriesAction(params?: {
  memory_type?: "event" | "topic" | "all";
  tag?: string;
  importance?: number;
  superseded?: boolean;
  sort_by?: string;
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}): Promise<MemoryListResponse> {
  const query = new URLSearchParams();
  if (params?.memory_type) query.set("memory_type", params.memory_type);
  if (params?.tag) query.set("tag", params.tag);
  if (params?.importance) query.set("importance", params.importance.toString());
  if (params?.superseded !== undefined) query.set("superseded", String(params.superseded));
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.order) query.set("order", params.order);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());

  const res = await apiFetch(`/memory?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch memories");
  return res.json();
}

export async function getEventAction(id: string | number): Promise<EventLog> {
  const res = await apiFetch(`/memory/events/${id}`);
  if (!res.ok) throw new Error("Failed to fetch event");
  return res.json();
}

export async function getTopicAction(id: string | number): Promise<TopicalMemory> {
  const res = await apiFetch(`/memory/topics/${id}`);
  if (!res.ok) throw new Error("Failed to fetch topic");
  return res.json();
}

export async function getTopicChainAction(id: string | number): Promise<MemoryRevisionChain> {
  const res = await apiFetch(`/memory/topics/${id}/chain`);
  if (!res.ok) throw new Error("Failed to fetch topic chain");
  return res.json();
}

export async function createEventAction(data: {
  subject?: string;
  event_time: string;
  content: string;
  tags?: string[];
  importance?: number;
  related_memory_ids?: number[];
}): Promise<EventLog> {
  const res = await apiFetch(`/memory/events`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create event");
  revalidatePath('/dashboard/memory');
  return res.json();
}

export async function updateEventAction(id: string | number, data: Partial<{
  subject: string;
  event_time: string;
  content: string;
  tags: string[];
  importance: number;
  related_memory_ids: number[];
}>): Promise<EventLog> {
  const res = await apiFetch(`/memory/events/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update event");
  revalidatePath('/dashboard/memory');
  return res.json();
}

export async function deleteEventAction(id: string | number): Promise<void> {
  const res = await apiFetch(`/memory/events/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error("Failed to delete event");
  revalidatePath('/dashboard/memory');
}

export async function createTopicAction(data: {
  subject?: string;
  content: string;
  tags?: string[];
  importance?: number;
}): Promise<TopicalMemory> {
  const res = await apiFetch(`/memory/topics`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create topic");
  revalidatePath('/dashboard/memory');
  return res.json();
}

export async function updateTopicAction(id: string | number, data: Partial<{
  subject: string;
  content: string;
  tags: string[];
  importance: number;
}>): Promise<TopicalMemory> {
  const res = await apiFetch(`/memory/topics/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update topic");
  revalidatePath('/dashboard/memory');
  return res.json();
}

export async function supersedeTopicAction(
  id: string | number,
  content: string,
  subject?: string,
  tags?: string[]
): Promise<TopicalMemory> {
  const res = await apiFetch(`/memory/topics/${id}/supersede?content=${encodeURIComponent(content)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, tags }),
  });
  if (!res.ok) throw new Error("Failed to supersede topic");
  revalidatePath('/dashboard/memory');
  return res.json();
}

export async function deleteTopicAction(id: string | number): Promise<void> {
  const res = await apiFetch(`/memory/topics/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error("Failed to delete topic");
  revalidatePath('/dashboard/memory');
}

export async function searchMemoriesAction(query: string, memory_type?: "event" | "topic" | "all"): Promise<MemoryListResponse> {
  const params = new URLSearchParams({ q: query });
  if (memory_type) params.set("memory_type", memory_type);
  const res = await apiFetch(`/memory/search?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to search memories");
  return res.json();
}

export async function getMemoryTagsAction(): Promise<TagCountResponse> {
  const res = await apiFetch(`/memory/tags`);
  if (!res.ok) throw new Error("Failed to fetch tags");
  return res.json();
}
