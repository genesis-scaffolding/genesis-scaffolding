"""LLM package - provider-agnostic interface to various LLM backends.

The main entry point is get_llm_response() which routes to either:
- _anthropic: for providers that need Anthropic SDK (e.g., MiniMax)
- _litellm: for OpenAI-compatible providers (e.g., OpenRouter)
"""

from typing import Any

from ..schemas import LLMModelConfig, LLMProvider, LLMResponse, StreamCallback
from ._anthropic import _call_anthropic
from ._base import is_anthropic_provider
from ._litellm import get_llm_response as _litellm_get_llm_response
from .token_utils import count_tokens, get_max_context_tokens

__all__ = ["get_llm_response", "count_tokens", "get_max_context_tokens"]


async def get_llm_response(
    llm_model_config: LLMModelConfig,
    provider_config: LLMProvider,
    messages: list[Any],
    stream: bool = False,
    content_chunk_callbacks: list[StreamCallback] | None = None,
    reasoning_chunk_callbacks: list[StreamCallback] | None = None,
    tools: list[Any] | None = None,
) -> LLMResponse:
    """Execute a completion request against an LLM.

    Routes to the appropriate provider implementation based on the provider config.

    Args:
        llm_model_config: Model configuration (model name, params like max_tokens, temperature)
        provider_config: Provider configuration (base_url, api_key, provider name)
        messages: List of message dicts in OpenAI format
        stream: Whether to stream the response
        content_chunk_callbacks: Optional callbacks for content chunks
        reasoning_chunk_callbacks: Optional callbacks for reasoning/thinking chunks
        tools: Optional list of tool definitions in OpenAI format

    Returns:
        LLMResponse with content, reasoning_content, and tool_calls
    """
    if is_anthropic_provider(provider_config):
        return await _call_anthropic(
            llm_model_config,
            provider_config,
            messages,
            stream,
            content_chunk_callbacks,
            reasoning_chunk_callbacks,
            tools,
        )

    # Default: use LiteLLM for OpenAI-compatible providers
    return await _litellm_get_llm_response(
        llm_model_config,
        provider_config,
        messages,
        stream,
        content_chunk_callbacks,
        reasoning_chunk_callbacks,
        tools,
    )
