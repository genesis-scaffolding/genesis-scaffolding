# LLM Client

## Overview

The LLM layer provides a provider-agnostic interface for calling language models. A single entry point routes requests to the appropriate implementation based on the provider. This makes it trivial to swap providers or add support for new ones.

## Entry Point

`get_llm_response()` is the single entry point. It takes:

- `llm_model_config` — Model name and per-call params (temperature, max_tokens, etc.)
- `provider_config` — Provider name, base_url, api_key
- `messages` — Messages in OpenAI format ({role, content})
- `stream` — Whether to stream the response
- `content_chunk_callbacks` — Called for each content chunk
- `reasoning_chunk_callbacks` — Called for each reasoning/thinking chunk
- `tools` — Tool definitions in OpenAI function-calling format

Returns: `LLMResponse(content, reasoning_content, tool_calls)`

## Provider Routing

Routing is simple: if the provider is MiniMax (Anthropic-compatible), use the Anthropic SDK. Everything else uses LiteLLM.

This split exists because MiniMax has incompatibilities with LiteLLM's handling of extended thinking blocks.

## LiteLLM Implementation

Used for OpenAI-compatible providers (OpenRouter, local llama.cpp, LM Studio, etc.). Delegates to `litellm.acompletion()`.

Key capabilities:
- Handles streaming with callbacks for both content and reasoning_content (OpenAI's extended reasoning)
- Parses tool calls from streaming chunks
- Enables usage metadata via stream_options

## Anthropic SDK Implementation

Used for MiniMax and similar Anthropic-compatible providers.

**Message format conversion** — OpenAI format differs from Anthropic's:

| OpenAI | Anthropic |
|--------|-----------|
| role: system | Extracted to separate system param |
| content: str | content: [{"type": "text", "text": "..."}] |
| role: tool | role: user with tool_result blocks |
| tool_calls: [...] | content: [{"type": "tool_use", ...}] blocks |
| parameters in tools | input_schema in tools |

Two conversion functions handle this:
- `_convert_messages_for_anthropic()` — splits system messages out, wraps content in blocks, converts tool roles
- `_convert_tools_for_anthropic()` — maps parameters to input_schema

**Thinking block support** — When a provider emits thinking blocks (extended reasoning), they are streamed via `reasoning_chunk_callbacks` and accumulated in `reasoning_content`.

## Data Schemas

**LLMProvider:**
- name: provider name (e.g., "openrouter")
- base_url: API base URL
- api_key: secret key

Configured per-user via the frontend. Users select which provider when creating a chat session.

**LLMModelConfig:**
- model: model name (e.g., "anthropic/claude-3-5-sonnet")
- params: dict of per-call parameters — max_tokens, temperature, reasoning_effort, etc.

**LLMResponse:**
- content: text response
- reasoning_content: extended thinking/reasoning (if any)
- tool_calls: list of structured tool call requests

**ToolCall:**
- id: unique call ID
- function_name: tool name
- arguments: raw JSON string of arguments

## Streaming and Callbacks

Three separate callback streams:

| Callback | Called when |
|----------|-------------|
| content_chunk_callbacks | Each text content delta arrives |
| reasoning_chunk_callbacks | Each reasoning/thinking delta arrives |
| tool callbacks in agent loop | Tool starts and completes |

Callbacks are asyncio.gather-ed for parallel invocation, ensuring minimal latency between receiving a chunk and notifying all subscribers.

## Key Design Decisions

1. **Single entry point** — `get_llm_response()` hides all routing. Adding a new provider implementation only requires adding a new module and updating the router.

2. **OpenAI format internally** — All message formatting is OpenAI-style internally. Provider-specific conversions happen at the boundary, keeping the core logic provider-agnostic.

3. **MiniMax as the Anthropic edge case** — MiniMax is the only current exception to the LiteLLM default. It uses the Anthropic SDK because LiteLLM's handling of MiniMax's extended thinking blocks is unreliable.

4. **Reasoning as a first-class output** — `reasoning_content` is a top-level field in `LLMResponse`, not buried in metadata. This makes it easy for the agent loop to inject reasoning into SSE streams or clipboard.

5. **Raw JSON strings for tool arguments** — `ToolCall.arguments` stores the raw JSON string. Parsing is deferred to the tool execution layer, which handles JSON decode errors gracefully.

## Token Utilities

`genesis_core.llm.token_utils` provides two public functions for token counting and model context limits:

### `count_tokens(messages, model) -> int`

Counts tokens in a list of LLM message dicts. Three tiers:

1. **Anthropic models** — calls `client.messages.count_tokens(messages, model)` from the official Anthropic SDK. Requires a model name (uses short-name extracted from provider-prefixed strings).
2. **OpenAI/LiteLLM models** — uses `litellm.tokenizer.encode()` to count tokens.
3. **Fallback** — 4-char-per-token heuristic (`len(text) // 4`).

Handles provider-prefixed model names (e.g., `openrouter/anthropic/claude-3-5-haiku`) by extracting the short name via `split("/")[-1]`.

### `get_max_context_tokens(model) -> int | None`

Returns the context window limit for a model string. Checks:
1. Exact match in the model map
2. Suffix match (last path component) for provider-prefixed names

Known models mapped:

| Model | Context Limit |
|-------|--------------|
| Claude Opus 4.6 / Sonnet 4.6 | 1,048,576 |
| Claude Haiku 4.5 | 204,800 |
| Claude Sonnet 4.5 | 204,800 |
| Claude Opus 4.5 | 1,048,576 |
| Claude 3.5 Haiku / Sonnet | 204,800 |
| Claude 3 Opus | 204,800 |
| Claude 3 Haiku | 204,800 |
| GPT-5.4 | 1,048,576 |
| GPT-5.4-mini / GPT-5.4-nano | 409,600 |
| GPT-4o / GPT-4o-mini | 128,000 |
| GPT-4 / GPT-4 Turbo | 128,000 |
| GPT-3.5 Turbo | 16,385 |
| Gemini 2.5 Pro / Flash | 1,048,576 |
| Gemini 2.0 Flash | 1,048,576 |
| Gemini 1.5 Flash / Pro | 1,048,576 |
| MiniMax M2.7 | 204,800 |
| GLM-4.7 / GLM-4.7-flash | 204,800 |
| Nemotron-3-Nano-30B-A3B-BF16 | 1,048,576 |

Returns `None` for unknown models.

## Related Modules

- `genesis_core.llm` — LLM provider abstraction (`get_llm_response()`, LiteLLM implementation, Anthropic SDK implementation)
- `genesis_core.llm.token_utils` — Token counting and model context limits
