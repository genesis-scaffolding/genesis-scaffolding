'use server';

import { apiGet, apiPost, apiPut, apiDelete } from '@/lib/api-client';

import { ApiError } from '@/types/api';

// Example: Fetch current user
export async function fetchCurrentUser() {
  try {
    return await apiGet('/users/me');
  } catch (error) {
    if (error instanceof ApiError) {
      console.error('Failed to fetch user:', error.message);
      return null;
    }
    throw error;
  }
}
