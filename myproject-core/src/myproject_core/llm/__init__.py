"""LLM package - provider-agnostic interface to various LLM backends."""

from ._anthropic import (
    get_llm_response as _anthropic_get_llm_response,
    _convert_messages_for_anthropic,
    _convert_tools_for_anthropic,
)
from ._litellm import get_llm_response as _litellm_get_llm_response
from ..schemas import LLMResponse

__all__ = ["get_llm_response"]


async def get_llm_response(
    llm_model_config,
    provider_config,
    messages,
    stream=False,
    content_chunk_callbacks=None,
    reasoning_chunk_callbacks=None,
    tools=None,
):
    """Stub - will be implemented in later task."""
    raise NotImplementedError("Placeholder")
