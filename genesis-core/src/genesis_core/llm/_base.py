"""Shared utilities for LLM provider routing."""

from ..schemas import LLMProvider


def is_anthropic_provider(provider_config: LLMProvider) -> bool:
    """Check if this provider should use the Anthropic SDK directly.

    Providers like MiniMax that are Anthropic-compatible but have issues
    with LiteLLM should use the official Anthropic SDK.
    """
    return provider_config.name == "minimax"
