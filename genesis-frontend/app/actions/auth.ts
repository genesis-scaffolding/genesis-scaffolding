'use server';

import { createSession, deleteSession, getAccessToken } from '@/lib/session';
import { authenticateUser, fetchUser, validateCredentials } from '@/lib/auth';
import { apiPost } from '@/lib/api-client';
import { redirect } from 'next/navigation';
import type { LoginState, LogoutState } from '@/types/auth';
import type { User } from '@/types/user'
import { RegisterState } from '@/types/auth';

export async function loginAction(
  prevState: LoginState,
  formData: FormData
): Promise<LoginState> {
  const username = formData.get('username') as string;
  const password = formData.get('password') as string;

  console.log("USERNAME: ", username)
  const validationError = validateCredentials(username, password);
  console.log("VALIDATION ERROR: ", validationError)
  if (validationError) {
    return { error: validationError };
  }


  const result = await authenticateUser(username, password);

  console.log("AUTHENTICATE USER RESULTS: ", result)

  if (!result.success) {
    return { error: result.error };
  }

  await createSession(
    result.data!.access_token,
    result.data!.refresh_token,
    result.data!.expires_in
  );

  return { success: true };
}

export async function logoutAction(
  prevState: LogoutState
): Promise<LogoutState> {
  try {
    await deleteSession();
    return { success: true };
  } catch (error) {
    console.error('Logout error:', error);
    return { error: 'Failed to logout' };
  }
}

export async function logout() {
  await deleteSession();
  redirect('/login');
}

export async function getCurrentUser(): Promise<User | null> {
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return null;
  }

  const user = await fetchUser(accessToken);

  // If token exists but user fetch fails, token is invalid
  if (!user) {
    return null;
  }

  return user;
}

export async function isAuthenticated(): Promise<boolean> {
  const accessToken = await getAccessToken();
  return accessToken !== null;
}


export async function registerAction(prevState: RegisterState, formData: FormData): Promise<RegisterState> {
  const username = formData.get('username') as string;
  const email = formData.get('email') as string;
  const full_name = formData.get('full_name') as string;
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;

  // Basic Validation
  if (password !== confirmPassword) {
    return {
      fieldErrors: { confirmPassword: ['Passwords do not match'] }
    };
  }
  // Sanitize: Convert empty strings to undefined so they are omitted or sent as null
  // FastAPI/Pydantic "str | None" fields often fail on "" if validators are present
  const payload = {
    username: username.trim(),
    password: password,
    email: email.trim() || null,
    full_name: full_name.trim() || null,
  };

  // Call FastAPI Backend
  try {
    await apiPost(`/users/`, payload);
  } catch (error: any) {
    // 3. Handle 422 Validation Errors from FastAPI
    if (error.status === 422 && error.data?.detail) {
      console.error("FastAPI Validation Error:", JSON.stringify(error.data.detail, null, 2));

      // Map FastAPI errors to our form fields
      const fieldErrors: Record<string, string[]> = {};

      error.data.detail.forEach((err: any) => {
        // err.loc usually looks like ["body", "username"]
        const fieldName = err.loc[err.loc.length - 1];
        fieldErrors[fieldName] = [err.msg];
      });

      return {
        fieldErrors,
        error: "Registration failed. Please check the highlighted fields."
      };
    }

    // Handle 400 Errors (e.g., "User already exists")
    if (error.status === 400) {
      return { error: error.data?.detail || "User already exists." };
    }

    return { error: "An unexpected error occurred during registration." };
  }

  redirect('/login?registered=true');
}
