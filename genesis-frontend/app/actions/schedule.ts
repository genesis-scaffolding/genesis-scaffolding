'use server';

import { getAccessToken } from '@/lib/session';
import { WorkflowSchedule, CreateScheduleInput, UpdateScheduleInput } from '@/types/schedule';
import { revalidatePath, revalidateTag } from 'next/cache';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

/**
 * Fetch all schedules owned by the current user
 */
export async function getSchedulesAction(): Promise<WorkflowSchedule[]> {
  const token = await getAccessToken();
  if (!token) throw new Error('Unauthorized');

  const response = await fetch(`${FASTAPI_URL}/schedules/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    next: { tags: ['schedules'], revalidate: 60 }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch schedules');
  }

  return response.json();
}

/**
 * Fetch one schedule object
 */
export async function getScheduleByIdAction(id: number): Promise<WorkflowSchedule> {
  const token = await getAccessToken();
  if (!token) throw new Error('Unauthorized');

  const response = await fetch(`${FASTAPI_URL}/schedules/${id}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    next: { tags: [`schedule-${id}`], revalidate: 60 }
  });

  if (!response.ok) {
    if (response.status === 404) throw new Error('Schedule not found');
    throw new Error('Failed to fetch schedule');
  }

  return response.json();
}

/**
 * Create a new workflow schedule
 */
export async function createScheduleAction(data: CreateScheduleInput): Promise<WorkflowSchedule> {
  const token = await getAccessToken();
  if (!token) throw new Error('Unauthorized');

  const response = await fetch(`${FASTAPI_URL}/schedules/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create schedule');
  }

  const newSchedule = await response.json();

  revalidatePath('/dashboard/schedules');
  revalidateTag('schedules', 'max');

  return newSchedule;
}

/**
 * Update an existing schedule (or toggle enabled status)
 */
export async function updateScheduleAction(
  scheduleId: number,
  data: UpdateScheduleInput
): Promise<WorkflowSchedule> {
  const token = await getAccessToken();
  if (!token) throw new Error('Unauthorized');

  const response = await fetch(`${FASTAPI_URL}/schedules/${scheduleId}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to update schedule');
  }

  const updated = await response.json();

  revalidatePath('/dashboard/schedules');
  revalidateTag('schedules', 'max');

  return updated;
}

/**
 * Delete a schedule
 */
export async function deleteScheduleAction(scheduleId: number): Promise<void> {
  const token = await getAccessToken();
  if (!token) throw new Error('Unauthorized');

  const response = await fetch(`${FASTAPI_URL}/schedules/${scheduleId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to delete schedule');
  }

  revalidatePath('/dashboard/schedules');
  revalidateTag('schedules', 'max');
}
