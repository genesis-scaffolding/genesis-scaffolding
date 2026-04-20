'use server'

import { apiFetch } from "@/lib/api-client";
import { revalidatePath } from "next/cache";
import {
  LLMConfigRead,
  LLMProvider,
  LLMModelConfig
} from "@/types/llm";

// The path where the settings page is located for cache revalidation
const SETTINGS_PATH = "/dashboard/settings/llm";

/**
 * GET /configs/llm/
 * Retrieves the merged system and user configurations.
 */
export async function getLLMConfigAction(): Promise<LLMConfigRead> {
  const res = await apiFetch("/configs/llm/");

  if (!res.ok) {
    throw new Error("Failed to fetch LLM configuration");
  }

  return res.json();
}

/**
 * POST /configs/llm/providers/{nickname}
 * Creates or updates an LLM provider.
 */
export async function saveProviderAction(nickname: string, data: LLMProvider) {
  const res = await apiFetch(`/configs/llm/providers/${nickname}`, {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save provider '${nickname}'`);
  }

  revalidatePath(SETTINGS_PATH);
  return res.json();
}

/**
 * DELETE /configs/llm/providers/{nickname}
 * Removes a provider. Note: Backend validates if models are using it.
 */
export async function deleteProviderAction(nickname: string) {
  const res = await apiFetch(`/configs/llm/providers/${nickname}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete provider '${nickname}'`);
  }

  revalidatePath(SETTINGS_PATH);
}

/**
 * POST /configs/llm/models/{nickname}
 * Creates or updates an LLM model configuration.
 */
export async function saveModelAction(nickname: string, data: LLMModelConfig) {
  const res = await apiFetch(`/configs/llm/models/${nickname}`, {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to save model '${nickname}'`);
  }

  revalidatePath(SETTINGS_PATH);
  return res.json();
}

/**
 * DELETE /configs/llm/models/{nickname}
 * Removes a model. Note: Backend prevents deleting the default model.
 */
export async function deleteModelAction(nickname: string) {
  const res = await apiFetch(`/configs/llm/models/${nickname}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete model '${nickname}'`);
  }

  revalidatePath(SETTINGS_PATH);
}

/**
 * PATCH /configs/llm/settings
 * Updates general settings like the default_model pointer.
 */
export async function updateDefaultModelAction(defaultModel: string) {
  const res = await apiFetch(`/configs/llm/settings`, {
    method: 'PATCH',
    body: JSON.stringify({ default_model: defaultModel }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update default model setting");
  }

  revalidatePath(SETTINGS_PATH);
  return res.json();
}
