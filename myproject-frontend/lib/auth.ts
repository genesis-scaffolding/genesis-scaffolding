import type { TokenResponse } from '@/types/auth';
import type { User } from '@/types/user';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

/**
 * Refresh access token using refresh token.
 * Does NOT persist tokens - caller is responsible for that.
 * Works in both Route Handlers and Edge Runtime (middleware).
 */
export async function refreshAccessToken(refreshToken: string): Promise<TokenResponse | null> {
  try {
    const response = await fetch(`${FASTAPI_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('Token refresh failed:', error);
    return null;
  }
}

/**
 * Authenticate user with FastAPI backend
 */
export async function authenticateUser(
  username: string,
  password: string
): Promise<{ success: boolean; data?: TokenResponse; error?: string }> {
  try {
    const response = await fetch(`${FASTAPI_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        username,
        password,
        grant_type: 'password',
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return {
        success: false,
        error: error.detail || 'Invalid credentials',
      };
    }

    const data: TokenResponse = await response.json();
    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error('Authentication error:', error);
    return {
      success: false,
      error: 'An error occurred during authentication',
    };
  }
}

/**
 * Fetch user data from FastAPI
 */
export async function fetchUser(accessToken: string): Promise<User | null> {
  try {
    const response = await fetch(`${FASTAPI_URL}/users/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('Fetch user error:', error);
    return null;
  }
}

/**
 * Validate credentials
 */
export function validateCredentials(
  username: string,
  password: string
): string | null {
  if (!username || !password) {
    return 'Username and password are required';
  }

  if (username.length < 3) {
    return 'Username must be at least 3 characters';
  }

  if (password.length < 6) {
    return 'Password must be at least 6 characters';
  }

  return null;
}
