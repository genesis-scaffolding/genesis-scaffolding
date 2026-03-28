# LLM Package Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the giant `llm.py` module into an `llm/` package with separate modules for different LLM providers (Anthropic, LiteLLM), while preserving the same public interface that `agent.py` depends on.

**Architecture:** The `llm/` package acts as an orchestrator that routes requests to the appropriate provider-specific implementation. The public interface `get_llm_response()` remains unchanged, so no changes needed to `agent.py` or other consumers.

**Tech Stack:** Python async/await, Anthropic SDK, LiteLLM

---

## File Structure

### Current
```
myproject_core/src/myproject_core/llm.py  # ~460 lines giant module
```

### After Refactor
```
myproject_core/src/myproject_core/llm/
  __init__.py      # Orchestrator: get_llm_response() routes to correct provider
  _base.py         # Shared: provider detection, type guards
  _anthropic.py    # Anthropic SDK path: _call_anthropic, stream/nonstream parsers
  _litellm.py      # LiteLLM path: litellm streaming/nonstream handling
```

**No changes needed to `agent.py`** - the import `from .llm import get_llm_response` will continue to work because `llm/__init__.py` will re-export it.

---

### Task 1: Create `llm/` directory and `_base.py`

**Files:**
- Create: `myproject-core/src/myproject_core/llm/__init__.py`
- Create: `myproject-core/src/myproject_core/llm/_base.py`
- Modify: `myproject-core/src/myproject_core/llm.py` (to be deleted after)

- [ ] **Step 1: Create `llm/` directory**

Run: `mkdir -p myproject-core/src/myproject_core/llm`

- [ ] **Step 2: Create `llm/_base.py`** with provider detection

```python
"""Shared utilities for LLM provider routing."""

from ..schemas import LLMProvider


def is_anthropic_provider(provider_config: LLMProvider) -> bool:
    """Check if this provider should use the Anthropic SDK directly.

    Providers like MiniMax that are Anthropic-compatible but have issues
    with LiteLLM should use the official Anthropic SDK.
    """
    return provider_config.name == "minimax"
```

- [ ] **Step 3: Create `llm/__init__.py`** with re-export stub

```python
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
    """Stub - will be implemented in Step 4."""
    raise NotImplementedError("Placeholder")
```

- [ ] **Step 4: Commit**

```bash
git add myproject-core/src/myproject_core/llm/
git commit -m "feat(llm): create llm package structure with _base.py"
```

---

### Task 2: Extract Anthropic path to `_anthropic.py`

**Files:**
- Create: `myproject-core/src/myproject_core/llm/_anthropic.py`
- Modify: `myproject-core/src/myproject_core/llm/__init__.py`

- [ ] **Step 1: Create `llm/_anthropic.py`** with Anthropic-specific code

```python
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
                idx = event.index
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
                idx = event.index

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
    for idx, tc in sorted(tool_calls_dict.items()):
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
```

- [ ] **Step 2: Commit**

```bash
git add myproject-core/src/myproject_core/llm/_anthropic.py
git commit -m "feat(llm): extract Anthropic SDK path to _anthropic.py"
```

---

### Task 3: Extract LiteLLM path to `_litellm.py`

**Files:**
- Create: `myproject-core/src/myproject_core/llm/_litellm.py`
- Modify: `myproject-core/src/myproject_core/llm/__init__.py`

- [ ] **Step 1: Create `llm/_litellm.py`** with LiteLLM code

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add myproject-core/src/myproject_core/llm/_litellm.py
git commit -m "feat(llm): extract LiteLLM path to _litellm.py"
```

---

### Task 4: Wire up `__init__.py` orchestrator

**Files:**
- Modify: `myproject-core/src/myproject_core/llm/__init__.py`

- [ ] **Step 1: Replace `__init__.py` with full orchestrator implementation**

```python
"""LLM package - provider-agnostic interface to various LLM backends.

The main entry point is get_llm_response() which routes to either:
- _anthropic: for providers that need Anthropic SDK (e.g., MiniMax)
- _litellm: for OpenAI-compatible providers (e.g., OpenRouter)
"""

from typing import Any

from ._anthropic import (
    _call_anthropic,
    _convert_messages_for_anthropic,
    _convert_tools_for_anthropic,
)
from ._base import is_anthropic_provider
from ._litellm import get_llm_response as _litellm_get_llm_response
from ..schemas import LLMModelConfig, LLMProvider, LLMResponse, StreamCallback

__all__ = ["get_llm_response"]


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
```

- [ ] **Step 2: Commit**

```bash
git add myproject-core/src/myproject_core/llm/__init__.py
git commit -m "feat(llm): wire up __init__.py as orchestrator"
```

---

### Task 5: Delete old `llm.py` and verify imports

**Files:**
- Delete: `myproject-core/src/myproject_core/llm.py`
- Verify: `myproject-core/src/myproject_core/agent.py` imports still work

- [ ] **Step 1: Delete old `llm.py`**

Run: `rm myproject-core/src/myproject_core/llm.py`

- [ ] **Step 2: Verify agent.py import works**

Run: `cd myproject-core && python -c "from src.myproject_core.agent import Agent; print('Import OK')"`

Expected: `Import OK`

- [ ] **Step 3: Commit deletion**

```bash
git add -A
git commit -m "refactor(llm): convert llm.py to llm/ package"
```

---

### Task 6: Remove debug print statements

**Files:**
- Modify: `myproject-core/src/myproject_core/llm/_anthropic.py`

- [ ] **Step 1: Remove debug print statements**

The debug prints were added during troubleshooting. Remove all print statements with `[DEBUG]`, `[STREAM DEBUG]`, `[TOOL DEBUG]`, `[TOOL RESULT DEBUG]`, `[MESSAGE DEBUG]`, `[TOOL RESULT DEBUG]` prefixes.

- [ ] **Step 2: Verify functionality still works**

Run a quick test or let the user verify with their test case.

- [ ] **Step 3: Commit**

```bash
git add myproject-core/src/myproject_core/llm/_anthropic.py
git commit -m "chore(llm): remove debug print statements"
```

---

### Task 7: Verify end-to-end with tool call

**Files:**
- None (testing)

- [ ] **Step 1: User tests tool call flow**

User runs the same test that triggered tool calls earlier to verify everything works.

- [ ] **Step 2: If all good, final commit if needed**

Any final cleanup commits as needed.
