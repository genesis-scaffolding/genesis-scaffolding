/**
 * Configuration for an LLM API provider (e.g., OpenRouter, OpenAI, Anthropic).
 * The 'nickname' used as the key in the backend dictionary is passed in the URL.
 */
export interface LLMProvider {
  name?: string;           // Optional, defaults to "openrouter"
  base_url?: string;       // Optional, defaults to "https://openrouter.ai/api/v1"
  api_key: string;         // Required field
}

/**
 * Configuration for a specific model instance.
 * @param provider - Must match a 'nickname' key in the providers dictionary.
 * @param model - The actual model string passed to LiteLLM (e.g., "anthropic/claude-3-opus").
 * @param params - Flexible arguments like temperature, max_tokens, reasoning_effort, etc.
 */
export interface LLMModelConfig {
  provider: string;
  model: string;
  params: Record<string, any>; // Dict[str, Any] in Python
}

/**
 * The full configuration object returned by GET /configs/llm/
 * Providers and Models are dictionaries where the key is a user-defined "nickname".
 */
export interface LLMConfigRead {
  providers: Record<string, LLMProvider>;
  models: Record<string, LLMModelConfig>;
  default_model: string;
}

/**
 * Helper type for handling the 'nickname' alongside the data 
 * during Form/Dialog operations.
 */
export interface LLMProviderWithNickname extends LLMProvider {
  nickname: string;
}

export interface LLMModelWithNickname extends LLMModelConfig {
  nickname: string;
}
