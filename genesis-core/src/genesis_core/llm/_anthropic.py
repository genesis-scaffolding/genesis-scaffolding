"""Anthropic SDK implementation for Minimax and similar providers."""

import asyncio
import json
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from ..schemas import LLMModelConfig, LLMProvider, LLMResponse, StreamCallback, ToolCall


def _convert_tools_for_anthropic(tools: list[dict]) -> list[dict]:
    """Convert OpenAI function-calling format to Anthropic tool format.

    Anthropic uses 'input_schema' instead of 'parameters' for the JSON Schema.
    The JSON Schema itself remains unchanged.
    """
    if not tools:
        return []

    anthropic_tools = []
    for tool in tools:
        func = tool.get("function", {})
        anthropic_tools.append(
            {
                "type": "tool",
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            }
        )
    return anthropic_tools


def _convert_messages_for_anthropic(
    messages: list[dict],
) -> tuple[list[dict], str | None]:
    """Convert message list to Anthropic API format.

    Anthropic expects message content as {"type": "text", "text": "..."} blocks
    instead of plain strings. System messages are extracted and returned separately.

    Returns:
        Tuple of (anthropic_messages, system_prompt) where system_prompt is the
        combined content of any system messages, or None if no system messages.
    """
    anthropic_messages = []
    system_parts = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        # System messages - extract to separate system_prompt (Anthropic doesn't accept role=system in messages array)
        if role == "system":
            system_parts.append(content)
            continue

        # Tool messages become user messages with tool_result content blocks
        if role == "tool":
            tool_use_id = msg.get("tool_call_id", "")
            tool_content = content
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_content,
                        }
                    ],
                }
            )
            continue

        # Assistant messages may have tool_calls that need to be converted to tool_use blocks
        if role == "assistant" and msg.get("tool_calls"):
            tool_calls = msg["tool_calls"]
            content_blocks = []
            if content:
                content_blocks.append({"type": "text", "text": content})
            for tc in tool_calls:
                func = tc.get("function", {})
                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    }
                )
            anthropic_messages.append({"role": role, "content": content_blocks})
        # Regular messages - content can be string or list of blocks
        elif isinstance(content, str):
            anthropic_messages.append({"role": role, "content": [{"type": "text", "text": content}]})
        else:
            anthropic_messages.append({"role": role, "content": content})

    system_prompt = "\n\n".join(system_parts) if system_parts else None
    return anthropic_messages, system_prompt


async def _call_anthropic(
    llm_model_config: LLMModelConfig,
    provider_config: LLMProvider,
    messages: list[Any],
    stream: bool,
    content_chunk_callbacks: list[StreamCallback] | None,
    reasoning_chunk_callbacks: list[StreamCallback] | None,
    tools: list[Any] | None,
) -> LLMResponse:
    """Use official Anthropic SDK for Minimax and similar providers."""
    client = anthropic.Anthropic(
        api_key=provider_config.api_key,
        base_url=str(provider_config.base_url) if provider_config.base_url else None,
    )

    anthropic_messages, extracted_system = _convert_messages_for_anthropic(messages)
    anthropic_tools = _convert_tools_for_anthropic(tools) if tools else None

    params: dict[str, Any] = {
        "model": llm_model_config.model,
        "messages": anthropic_messages,
        "max_tokens": llm_model_config.params.get("max_tokens", 4096),
    }
    if anthropic_tools:
        params["tools"] = anthropic_tools

    if "system" in llm_model_config.params:
        params["system"] = llm_model_config.params["system"]
    elif extracted_system:
        params["system"] = extracted_system

    if "temperature" in llm_model_config.params:
        params["temperature"] = llm_model_config.params["temperature"]

    if stream:
        async_client = AsyncAnthropic(
            api_key=provider_config.api_key,
            base_url=str(provider_config.base_url) if provider_config.base_url else None,
        )
        return await _parse_anthropic_stream(
            async_client,
            params,
            content_chunk_callbacks,
            reasoning_chunk_callbacks,
        )
    return _parse_anthropic_nonstream(client.messages.create(**params))


def _parse_anthropic_nonstream(response: anthropic.types.Message) -> LLMResponse:
    """Parse non-streaming Anthropic response."""
    full_content = ""
    full_reasoning_content = ""
    tool_calls_list: list[dict[str, Any]] = []

    for block in response.content:
        if block.type == "text":
            full_content += block.text
        elif block.type == "thinking":
            full_reasoning_content += block.thinking
        elif block.type == "tool_use":
            args_dict = block.input if isinstance(block.input, dict) else {}
            tool_calls_list.append(
                {
                    "id": block.id,
                    "name": block.name,
                    "args": args_dict,
                }
            )

    final_tool_calls = []
    for tc in tool_calls_list:
        args_str = tc.get("args", {})
        if isinstance(args_str, dict):
            args_str = json.dumps(args_str)
        final_tool_calls.append(
            ToolCall(
                id=tc["id"],
                function_name=tc["name"],
                arguments=str(args_str),
            )
        )

    return LLMResponse(
        content=full_content,
        reasoning_content=full_reasoning_content,
        tool_calls=final_tool_calls,
    )


async def _parse_anthropic_stream(
    client: AsyncAnthropic,
    params: dict[str, Any],
    content_chunk_callbacks: list[StreamCallback] | None,
    reasoning_chunk_callbacks: list[StreamCallback] | None,
) -> LLMResponse:
    """Parse streaming Anthropic response using async iteration for real-time callbacks."""
    full_content = ""
    full_reasoning_content = ""
    tool_calls_dict: dict[int, dict[str, Any]] = {}

    async with client.messages.stream(**params) as stream:
        async for event in stream:
            event_type = getattr(event, "type", None)

            if event_type == "content_block_start":
                idx = event.index  # type: ignore
                content_block = getattr(event, "content_block", None)
                if content_block and getattr(content_block, "type", None) == "tool_use":
                    tool_calls_dict[idx] = {
                        "id": getattr(content_block, "id", "") or "",
                        "name": getattr(content_block, "name", "") or "",
                        "args": "",
                    }

            elif event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                if not delta:
                    continue

                delta_type = getattr(delta, "type", None)
                idx = event.index  # type: ignore

                if delta_type == "text_delta":
                    text_value = getattr(delta, "text", "") or ""
                    if text_value:
                        full_content += text_value
                        if content_chunk_callbacks:
                            await asyncio.gather(*[cb(text_value) for cb in content_chunk_callbacks])

                elif delta_type == "thinking_delta":
                    thinking_value = getattr(delta, "thinking", "") or ""
                    if thinking_value:
                        full_reasoning_content += thinking_value
                        if reasoning_chunk_callbacks:
                            await asyncio.gather(*[cb(thinking_value) for cb in reasoning_chunk_callbacks])

                elif delta_type == "input_json_delta":
                    partial_json = getattr(delta, "partial_json", "") or ""
                    if partial_json:
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {"id": "", "name": "", "args": ""}
                        tool_calls_dict[idx]["args"] = tool_calls_dict[idx].get("args", "") + partial_json

    final_tool_calls = []
    for _idx, tc in sorted(tool_calls_dict.items()):
        args_str = tc.get("args", "")
        if isinstance(args_str, dict):
            args_str = json.dumps(args_str)
        final_tool_calls.append(
            ToolCall(
                id=tc.get("id", ""),
                function_name=tc.get("name", ""),
                arguments=args_str,
            )
        )

    return LLMResponse(
        content=full_content,
        reasoning_content=full_reasoning_content,
        tool_calls=final_tool_calls,
    )
