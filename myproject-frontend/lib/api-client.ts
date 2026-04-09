import { getAccessToken, getRefreshToken, createSession, deleteSession } from '@/lib/session';
import { refreshAccessToken } from '@/lib/auth';
import { ApiError } from '@/types/api';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
  requireAuth?: boolean;
}

export async function apiFetch(
  endpoint: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { requireAuth = true, ...fetchOptions } = options;

  let accessToken = requireAuth ? await getAccessToken() : null;

  const headers = new Headers(fetchOptions.headers);

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  if (!headers.has('Content-Type') && fetchOptions.body) {
    headers.set('Content-Type', 'application/json');
  }

  let response = await fetch(`${FASTAPI_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  // If 401 and we need auth, try to refresh token
  if (response.status === 401 && requireAuth) {
    const refreshToken = await getRefreshToken();

    if (refreshToken) {
      // Try to refresh the access token
      const refreshed = await refreshAccessToken(refreshToken);

      if (refreshed) {
        // Persist new tokens in session
        await createSession(
          refreshed.access_token,
          refreshed.refresh_token,
          refreshed.expires_in
        );
        // Retry the original request with new access token
        headers.set('Authorization', `Bearer ${refreshed.access_token}`);
        response = await fetch(`${FASTAPI_URL}${endpoint}`, {
          ...fetchOptions,
          headers,
        });
      } else {
        // Refresh failed, clear session
        await deleteSession();
      }
    }
  }

  return response;
}

// Convenience methods
export async function apiGet(endpoint: string, options?: FetchOptions) {
  const response = await apiFetch(endpoint, { ...options, method: 'GET' });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API error: ${response.statusText}`,
      await response.json().catch(() => null)
    );
  }

  return response.json();
}

export async function apiPost(
  endpoint: string,
  data?: any,
  options?: FetchOptions
) {
  const response = await apiFetch(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API error: ${response.statusText}`,
      await response.json().catch(() => null)
    );
  }

  return response.json();
}

export async function apiPut(
  endpoint: string,
  data?: any,
  options?: FetchOptions
) {
  const response = await apiFetch(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API error: ${response.statusText}`,
      await response.json().catch(() => null)
    );
  }

  return response.json();
}

export async function apiDelete(endpoint: string, options?: FetchOptions) {
  const response = await apiFetch(endpoint, { ...options, method: 'DELETE' });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API error: ${response.statusText}`,
      await response.json().catch(() => null)
    );
  }

  // DELETE might return no content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function apiPatch(
  endpoint: string,
  data?: any,
  options?: FetchOptions
) {
  const response = await apiFetch(endpoint, {
    ...options,
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `API error: ${response.statusText}`,
      await response.json().catch(() => null)
    );
  }

  return response.json();
}
