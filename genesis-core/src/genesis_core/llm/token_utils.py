"""Token counting utilities for LLM message lists and model context limits."""

from typing import Any

# Anthropic models — use official Anthropic SDK for token counting
# Keys: bare model names and common prefixed variants
_ANTHROPIC_MODEL_CONTEXTS: dict[str, int] = {
    # Claude 4.6 (latest)
    "claude-opus-4-6": 1048576,
    "claude-sonnet-4-6": 1048576,
    "claude-haiku-4-5-20251001": 204800,
    "claude-haiku-4-5": 204800,
    # Legacy Claude 4.5
    "claude-sonnet-4-5-20250929": 204800,
    "claude-sonnet-4-5": 204800,
    "claude-opus-4-5-20251101": 1048576,
    "claude-opus-4-5": 1048576,
    "claude-opus-4-1-20250805": 204800,
    "claude-opus-4-1": 204800,
    "claude-sonnet-4-20250514": 204800,
    "claude-sonnet-4-0": 204800,
    "claude-opus-4-20250514": 204800,
    "claude-opus-4-0": 204800,
    # Legacy Claude 3.5
    "claude-3-5-haiku-20241022": 204800,
    "claude-3-5-sonnet-20241022": 204800,
    "claude-3-opus-20240229": 204800,
    "claude-3-sonnet-20240229": 204800,
    # Legacy Claude 3
    "claude-3-haiku-20240307": 204800,
    # MiniMax (uses Anthropic SDK on the inference side)
    "minimax/M2.7": 204800,
    "minimax/m2.7": 204800,
    # Zhipu AI GLM (uses Anthropic SDK on the inference side)
    "glm-4.7": 204800,
    "glm-4.7-flashx": 204800,
    "glm-4.7-flash": 204800,
}

# OpenAI and other LiteLLM models — use litellm tokenizer for token counting
_LITELLM_MODEL_CONTEXTS: dict[str, int] = {
    # OpenAI GPT-5 series
    "gpt-5.4": 1048576,
    "gpt-5.4-mini": 409600,
    "gpt-5.4-nano": 409600,
    # OpenAI GPT-4o series
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 128000,
    "gpt-3.5-turbo": 16385,
    # OpenAI provider prefixes
    "openai/gpt-5.4": 1048576,
    "openai/gpt-5.4-mini": 409600,
    "openai/gpt-5.4-nano": 409600,
    "openai/gpt-4o": 128000,
    "openai/gpt-4o-mini": 128000,
    # OpenRouter prefixes
    "openrouter/openai/gpt-5.4": 1048576,
    "openrouter/openai/gpt-5.4-mini": 409600,
    "openrouter/openai/gpt-4o": 128000,
    "openrouter/openai/gpt-4o-mini": 128000,
    # Google Gemini
    "gemini-2.5-pro": 1048576,
    "gemini-2.5-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-2.0-flash-lite": 1048576,
    "gemini-1.5-flash": 1048576,
    "gemini-1.5-pro": 1048576,
    "gemini-1.0-pro": 32000,
    # Google provider prefix
    "google/gemini-2.5-pro": 1048576,
    "google/gemini-2.5-flash": 1048576,
    "google/gemini-2.0-flash": 1048576,
    "google/gemini-1.5-flash": 1048576,
    "google/gemini-1.5-pro": 1048576,
    # NVIDIA Nemotron (via vLLM, served as OpenAI-compatible)
    "nvidia/Nemotron-3-Nano-30B-A3B-BF16": 1048576,
    "Nemotron-3-Nano-30B-A3B-BF16": 1048576,
}


def get_max_context_tokens(model: str) -> int | None:
    """Return context window limit for a model string, or None if unknown.

    Handles bare model names (e.g. "claude-3-5-haiku-20241022") and
    provider-prefixed names (e.g. "openrouter/anthropic/claude-3-5-haiku").
    """
    # 1. Exact match
    if model in _ANTHROPIC_MODEL_CONTEXTS:
        return _ANTHROPIC_MODEL_CONTEXTS[model]
    if model in _LITELLM_MODEL_CONTEXTS:
        return _LITELLM_MODEL_CONTEXTS[model]

    # 2. Suffix match — try the last path component (handles "openrouter/anthropic/claude-3-5-haiku")
    short_name = model.split("/")[-1]
    if short_name in _ANTHROPIC_MODEL_CONTEXTS:
        return _ANTHROPIC_MODEL_CONTEXTS[short_name]
    if short_name in _LITELLM_MODEL_CONTEXTS:
        return _LITELLM_MODEL_CONTEXTS[short_name]

    return None


def count_tokens(messages: list[dict[str, Any]], model: str) -> int:
    """
    Count tokens for a list of LLM message dicts.

    For Anthropic models (claude-*, GLM-4.7, minimax/M2.7): uses official anthropic
    messages.count_tokens API. For OpenAI/LiteLLM models: uses litellm.tokenizer.
    Fallback: 4-char-per-token heuristic.
    """
    short_name = model.split("/")[-1]
    model_lower = model.lower()
    short_lower = short_name.lower()

    # Anthropic-side models — Anthropic SDK, GLM-4.7, MiniMax M2.7
    if "claude" in model_lower or "claude" in short_lower or "glm-4.7" in model_lower or "glm-4.7" in short_lower or "minimax" in model_lower:
        try:
            import anthropic

            client = anthropic.Anthropic()
            result = client.messages.count_tokens(
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                model=short_name,
            )
            return result.input_tokens
        except Exception:
            return _heuristic(messages)

    # LiteLLM / OpenAI-compatible
    try:
        import litellm

        tokenizer = getattr(litellm, "tokenizer", None)
        if tokenizer:
            return len(tokenizer.encode(_flatten_messages(messages)))
    except Exception:
        pass

    return _heuristic(messages)


def _flatten_messages(messages: list[dict[str, Any]]) -> str:
    parts = []
    for msg in messages:
        parts.append(f"{msg.get('role', '')}: {msg.get('content', '')}")
    return "\n".join(parts)


def _heuristic(messages: list[dict[str, Any]]) -> int:
    return len(_flatten_messages(messages)) // 4
