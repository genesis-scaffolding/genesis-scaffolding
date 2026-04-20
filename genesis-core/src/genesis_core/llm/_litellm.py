"""LiteLLM implementation for OpenAI-compatible providers."""

import asyncio
from typing import Any, cast

import litellm
from litellm import CustomStreamWrapper, ModelResponse, acompletion
from litellm.types.utils import Choices, StreamingChoices

from ..schemas import LLMModelConfig, LLMProvider, LLMResponse, StreamCallback, ToolCall

litellm.suppress_debug_info = True


async def get_llm_response(
    llm_model_config: LLMModelConfig,
    provider_config: LLMProvider,
    messages: list[Any],
    stream=False,
    content_chunk_callbacks: list[StreamCallback] | None = None,
    reasoning_chunk_callbacks: list[StreamCallback] | None = None,
    tools: list[Any] | None = None,
) -> LLMResponse:
    """Execute LLM call via LiteLLM for OpenAI-compatible providers."""
    response: Any = await acompletion(
        api_base=provider_config.base_url,
        api_key=provider_config.api_key,
        model=f"{provider_config.name}/{llm_model_config.model}",
        messages=messages,
        stream=stream,
        stream_options={"include_usage": True},
        tools=tools,
        extra_headers={"Authorization": f"Bearer {provider_config.api_key}"},
        **llm_model_config.params,
    )

    full_content = ""
    full_reasoning_content = ""
    tool_calls_dict: dict[int, dict[str, Any]] = {}

    if stream:
        if not isinstance(response, CustomStreamWrapper):
            raise RuntimeError("Expected a stream from litellm but didn't get one.")

        async for chunk in response:
            choice = cast("StreamingChoices", chunk.choices[0])

            content = getattr(choice.delta, "content", "") or ""
            if content:
                full_content += content
                if content_chunk_callbacks:
                    await asyncio.gather(*[cb(content) for cb in content_chunk_callbacks])

            reasoning = getattr(choice.delta, "reasoning_content", "") or ""
            if reasoning:
                full_reasoning_content += reasoning
                if reasoning_chunk_callbacks:
                    await asyncio.gather(*[cb(reasoning) for cb in reasoning_chunk_callbacks])

            tool_calls = getattr(choice.delta, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {"id": "", "name": "", "args": ""}
                    if tc.id:
                        tool_calls_dict[idx]["id"] += tc.id
                    if tc.function.name:
                        tool_calls_dict[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls_dict[idx]["args"] += tc.function.arguments

    else:
        if not isinstance(response, ModelResponse):
            raise RuntimeError("Expected a ModelResponse from litellm but didn't get one.")

        choices = response.choices[0]
        choices = cast("Choices", choices)

        full_content = getattr(choices.message, "content", full_content)
        full_reasoning_content = getattr(choices.message, "reasoning_content", full_reasoning_content)

        tool_calls = getattr(choices.message, "tool_calls", None)
        if tool_calls:
            for i, tc in enumerate(tool_calls):
                tool_calls_dict[i] = {
                    "id": getattr(tc, "id", ""),
                    "name": getattr(tc.function, "name", ""),
                    "args": getattr(tc.function, "arguments", ""),
                }

    final_tool_calls = [
        ToolCall(id=v["id"], function_name=v["name"], arguments=v["args"]) for v in tool_calls_dict.values()
    ]
    return LLMResponse(
        content=full_content,
        reasoning_content=full_reasoning_content,
        tool_calls=final_tool_calls,
    )
