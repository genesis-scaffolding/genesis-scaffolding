import asyncio
from typing import Any, cast

from httpx import get
import litellm
from litellm import CustomStreamWrapper, ModelResponse, acompletion
from litellm.types.utils import Choices, StreamingChoices

from .configs import get_config
from .schemas import LLMModel, LLMProvider, LLMResponse, StreamCallback, ToolCall
from .utils import streamcallback_simple_print

litellm.suppress_debug_info = True  # Silences provider suggestion logs


async def get_llm_response(
    llm_model: LLMModel,
    messages: list[Any],
    stream=False,
    content_chunk_callbacks: list[StreamCallback] | None = None,
    reasoning_chunk_callbacks: list[StreamCallback] | None = None,
    tools: list[Any] | None = None,
) -> LLMResponse:
    """
    Executes a completion request against an LLM and handles both static and streaming outputs. This function is async by default.

    The caller receives full content and reasoning content from the LLM regardless of whether they stream or not.

    The caller can pass callback functions to handle each of the content and reasoning chunk coming from the model (e.g., to display to UI)

    Args:
        llm_model: An LLMModel configuration object containing provider credentials and model identifiers.
        messages: A list of message dictionaries (role/content) representing the conversation history.
        stream: If True, the function iterates over the response stream and triggers callbacks. Defaults to False.
        content_chunk_callbacks: An optional list of async functions triggered every time a new 'content' text chunk is received during streaming. Useful for real-time UI updates.
        reasoning_chunk_callbacks: An optional list of async functions triggered every time a 'reasoning_content' chunk (Chain-of-Thought) is received. Used for displaying the model's internal logic as it generates.

    Returns:
        LLMResponse: A custom object containing the fully accumulated 'content' and 'reasoning_content'.

    Raises:
        RuntimeError: If the returned LiteLLM object does not match the requested 'stream' mode.

    TODO:
        - Implement support for `tool_calls` and function calling logic within both the streaming and static response paths.
    """
    response: Any = await acompletion(
        base_url=llm_model.provider.base_url,
        api_key=llm_model.provider.api_key,
        model=llm_model.model,
        messages=messages,
        stream=stream,
        stream_options={"include_usage": True},
        tools=tools,
    )

    full_content = ""
    full_reasoning_content = ""
    tool_calls_dict = {}

    if stream:
        if not isinstance(response, CustomStreamWrapper):
            raise RuntimeError("Expected a stream from litellm but didn't get one.")
        full_content = ""
        full_reasoning_content = ""
        async for chunk in response:
            # This cast prevents pyright from assign the type of choice correctly to streaming choice
            choice = cast(StreamingChoices, chunk.choices[0])

            # Handle Content Chunk
            content = getattr(choice.delta, "content", "") or ""
            if content:
                full_content += content
                if content_chunk_callbacks:
                    await asyncio.gather(*[cb(content) for cb in content_chunk_callbacks])

            # Handle Reasoning Chunk
            reasoning = getattr(choice.delta, "reasoning_content", "") or ""
            if reasoning:
                full_reasoning_content += reasoning
                if reasoning_chunk_callbacks:
                    await asyncio.gather(*[cb(reasoning) for cb in reasoning_chunk_callbacks])

            # Handle tool call chunks
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

        # This cast prevents pyright from incorrectly assign the type of choice to be StreamingChoice
        choices = response.choices[0]
        choices = cast(Choices, choices)

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
        content=full_content, reasoning_content=full_reasoning_content, tool_calls=final_tool_calls
    )


async def main():
    settings = get_config()
    # We pull credentials from settings to build our Provider and Model schemas.
    llm_provider = LLMProvider(base_url=settings.llm.base_url, api_key=settings.llm.api_key)
    llm_model = LLMModel(provider=llm_provider, model=settings.llm.model)

    # 3. Execute the LLM Call with Streaming
    # Note how we use the SAME callback for both reasoning and content.
    # In a real UI, you might send reasoning to a 'thought bubble'
    # and content to the 'chat bubble'.
    llm_response = await get_llm_response(
        llm_model,
        [{"content": "Hello, how are you?", "role": "user"}],
        stream=True,
        content_chunk_callbacks=[streamcallback_simple_print],
        reasoning_chunk_callbacks=[streamcallback_simple_print],
    )

    # 4. Access the Final Accumulated Data
    # Even though we streamed the output above, the 'get_llm_response'
    # function has collected all chunks into a final LLMResponse object.
    print("\n\n--- SUMMARY ---")
    print(f"Reasoning content captured:\n{llm_response.reasoning_content}\n")
    print(f"Final response captured:\n{llm_response.content}\n")


if __name__ == "__main__":
    asyncio.run(main())
