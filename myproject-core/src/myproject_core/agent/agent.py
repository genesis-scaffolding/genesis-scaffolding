import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from myproject_tools.pdf import convert_pdf_to_markdown
from myproject_tools.registry import tool_registry
from myproject_tools.schema import ToolResult

from ..configs import get_config
from ..llm import get_llm_response, get_max_context_tokens
from ..persistent_memory.db import get_memory_session
from ..productivity.db import get_user_session
from ..prompts import BuildPromptConfig, build_system_prompt
from ..schemas import AgentConfig, StreamCallback, ToolCallback
from ..utils import streamcallback_simple_print
from .agent_memory import AgentMemory


class Agent:
    def __init__(
        self,
        agent_config: AgentConfig,
        memory: AgentMemory | None = None,
        timezone: str = "UTC",
        working_directory: Path | None = None,
        content_chunk_callbacks: list[StreamCallback] | None = None,
        reasoning_chunk_callbacks: list[StreamCallback] | None = None,
        user_db_url: str | None = None,
        memory_db_url: str | None = None,
        clipboard_item_ttl: int = 50,
    ) -> None:
        self.agent_config = agent_config
        if not agent_config.provider_config:
            raise Exception(f"Agent {agent_config.name} does not have LLM provider configuration.")

        if not agent_config.llm_config:
            raise Exception(f"Agent {agent_config.name} does not have llm configuration.")

        self.llm_model_config = agent_config.llm_config
        self.provider_config = agent_config.provider_config

        prompt_config = BuildPromptConfig(
            system_prompt=agent_config.system_prompt,
            allowed_tools=agent_config.allowed_tools,
            interactive=agent_config.interactive,
            has_memory_db=memory_db_url is not None,
            has_user_db=user_db_url is not None,
            has_working_directory=working_directory is not None,
        )
        system_prompt = build_system_prompt(prompt_config)
        self.memory = memory or AgentMemory(
            messages=[self._create_llm_message(role="system", content=system_prompt)],
            timezone=timezone,
            clipboard_item_ttl=clipboard_item_ttl,
        )

        self.stream = agent_config.interactive
        self.content_chunk_callbacks = content_chunk_callbacks
        self.reasoning_chunk_callbacks = reasoning_chunk_callbacks

        self.working_directory = working_directory
        if working_directory and not working_directory.exists():
            raise Exception(
                f"Agent {agent_config.name} was given a non-existent working directory: {working_directory}",
            )

        self.tools: list[Any] = []  # This will hold the tool instances
        self._resolve_tools()

        self.timezone = timezone  # Timezone for providing agent with accurate local time
        self.user_db_url = (
            user_db_url  # Passing connection string to user's private database for agent to use in tools
        )
        self.memory_db_url = memory_db_url  # Connection string to user's private memory database

        self.max_context_tokens = get_max_context_tokens(self.llm_model_config.model) or 0

    def _resolve_tools(self):
        """Attempts to import the tool registry and look up tools
        defined in allowed_tools.
        """
        try:
            for tool_name in self.agent_config.allowed_tools:
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    self.tools.append(tool)
                else:
                    # Silently ignore or log that a tool wasn't found
                    print(f"Warning: Tool '{tool_name}' not found in registry.")

        except ImportError:
            # If myproject_tools is not available, agent simply has no tools
            self.tools = []

    def _get_tool_definitions(self) -> list[dict]:
        """Returns the JSON schemas for all resolved tools for the LLM call."""
        return [t.to_llm_schema() for t in self.tools]

    def _create_llm_message(
        self,
        role: Literal["user", "assistant", "system", "tool"],
        content: str,
        reasoning_content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,  # Add this
        tool_call_id: str | None = None,  # Add this for tool responses
    ) -> dict[str, Any]:  # Explicitly return dict[str, Any]
        llm_message: dict[str, Any] = {"role": role, "content": content}

        if reasoning_content:
            llm_message["reasoning_content"] = reasoning_content
        if tool_calls:
            llm_message["tool_calls"] = tool_calls
        if tool_call_id:
            llm_message["tool_call_id"] = tool_call_id

        return llm_message

    async def _execute_tool_and_format(self, tool_id: str, name: str, args: dict, working_directory: Path):
        """Internal helper to run the tool and format the message for the LLM."""
        # 1. Look up tool
        tool = next((t for t in self.tools if t.name == name), None)

        try:
            if not tool:
                result_str = f"Error: Tool {name} not found."
            else:
                # Execute (Pure data generation)
                result: ToolResult = await tool.run(
                    working_directory=working_directory,
                    user_db_url=self.user_db_url,
                    memory_db_url=self.memory_db_url,
                    timezone=self.timezone,
                    **args,
                )

                # Side Effect: Add files to clipboard
                if result.status == "success" and result.files_to_add_to_clipboard:
                    for file_path in result.files_to_add_to_clipboard:
                        await self.add_file(file_path=file_path, working_directory=working_directory)

                # Side Effect: Add tool results to clipboard
                if result.status == "success" and result.results_to_add_to_clipboard:
                    self.memory.add_tool_results_to_clipboard(
                        tool_name=name,
                        tool_call_id=tool_id,
                        results=result.results_to_add_to_clipboard,
                    )

                # Side Effect: Pin productivity entities to clipboard
                if (
                    result.status == "success"
                    and hasattr(result, "entities_to_track")
                    and result.entities_to_track
                ):
                    for entity in result.entities_to_track:
                        self.memory.pin_entity(
                            item_type=entity.item_type,
                            item_id=entity.item_id,
                            resolution=entity.resolution,
                            ttl=entity.ttl,
                        )

                result_str = result.tool_response
        except Exception as e:
            # Uncaught error. This really should not happen as it messes up the agent
            result_str = f"Tool Execution Error: {e!s}"

        # Return the 'tool' role message required by LLM history
        return {"role": "tool", "tool_call_id": tool_id, "name": name, "content": result_str}

    def _log_debug_messages(self, messages: list[dict], turn: int):
        """Dumps the current message stack to a local JSON file for debugging."""
        timestamp = datetime.now().strftime("%H-%M-%S")
        debug_file = Path("debug_messages.json")

        # We append to the file so we can see the history of turns
        with open(debug_file, "a", encoding="utf-8") as f:
            log_entry = {
                "timestamp": timestamp,
                "agent": self.agent_config.name,
                "turn": turn,
                "messages": messages,
            }
            f.write(json.dumps(log_entry, indent=2) + "\n\n" + "=" * 50 + "\n\n")

    def _get_current_working_directory(self, working_directory: Path | None):
        current_working_directory = working_directory or self.working_directory
        if not current_working_directory:
            raise Exception(
                f"Failed to call agent {self.agent_config.name}: the agent was not created with a working directory, and none was given when calling step()",
            )
        return current_working_directory

    def _inject_clipboard(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Utility function for injecting clipboard into LLM context
        without mutating the original history list or its dictionaries.
        """
        last_user_index: int | None = None
        for i in range(len(history) - 1, -1, -1):
            if history[i]["role"] == "user":
                last_user_index = i
                break

        # Get the clipboard message (assuming this returns a dict like {"role": "...", "content": "..."})
        clipboard_msg = self.memory.get_clipboard_message(timezone=self.timezone)
        clipboard_text = clipboard_msg.get("content", "")

        # 1. Attach clipboard context directly into last tool response if it exists
        if history[-1]["role"] == "tool":
            # Create a SHALLOW COPY of the dictionary so we don't mutate the original
            tool_result_with_clipboard = history[-1].copy()
            tool_result_with_clipboard["content"] = (
                f"{tool_result_with_clipboard.get('content', '')}\n\nClipboard context:\n{clipboard_text}"
            )
            # Use [:-1] to only remove the last message we just replaced
            return history[:-1] + [tool_result_with_clipboard]

        # 2. Attach clipboard context just before last user message
        if last_user_index is not None:
            # Slicing creates a new list, so this is safe for the list structure
            return history[:last_user_index] + [clipboard_msg] + history[last_user_index:]

        # 3. Fringe case: No user message found. Append to end.
        return history + [clipboard_msg]

    async def step(
        self,
        input: str,
        working_directory: Path | None = None,
        stream: bool | None = None,
        content_chunk_callbacks: list[StreamCallback] | None = None,
        reasoning_chunk_callbacks: list[StreamCallback] | None = None,
        tool_start_callback: list[ToolCallback] | None = None,
        tool_result_callback: list[ToolCallback] | None = None,
        debug=False,
        max_turns: int = 20,  # Increased for long-horizon tasks
        max_repetitions: int = 3,  # Stop if same tool called N times
    ):
        """Agent calls LLM to progress to the next step
        The clipboard is injected to message list to send to LLM to provid the context
        Then, clipboard is removed so that it does not inflate the message history
        The agent would loop until max number of turn of until no more tool calls are detected.
        """
        # Fail fast if there is no working directory
        current_working_directory = self._get_current_working_directory(working_directory)

        # Add user message to memory
        self.memory.append_memory(self._create_llm_message(role="user", content=input))

        # Reduce ttl and remove any expire item from memory to save space
        self.memory.forget()

        # Remove the deleted files from the clipboard
        self.memory.remove_deleted_files(working_dir=current_working_directory)

        # Track tool call history to detect loops
        tool_call_history = []

        # Temp solution to observe the LLM response. Will migrate to something better later
        debug = True
        if debug:
            with open("debug_messages.json", "w") as f:
                f.write("")

        # Start the tool call loop
        # Significantly reduce the number of turn for testing
        for turn in range(max_turns):
            # Sync the productivity pinned entities
            if self.user_db_url and self.memory.agent_clipboard.pinned_entities:
                # get_user_session is a generator, so we iterate to get the session
                # and ensure it closes automatically afterwards
                for session in get_user_session(db_url=self.user_db_url):
                    self.memory.sync_entities(session, db_type="productivity")

            # Sync the memory pinned entities
            if self.memory_db_url and self.memory.agent_clipboard.pinned_entities:
                for session in get_memory_session(memory_db_url=self.memory_db_url):
                    self.memory.sync_entities(session, db_type="memory")

            # Sync memory tag hints
            if self.memory_db_url:
                for session in get_memory_session(memory_db_url=self.memory_db_url):
                    self.memory.sync_memory_tag_hints(session)
                    self.memory.sync_user_profile(session)

            # Build the ephemeral payload for the LLM
            # Current memory.messages is [..., UserMsg]
            history = self.memory.get_messages()

            # If we are nearing the turn limit, nudge the model
            # This message would not be embedded into the chat history
            if turn == max_turns - 3:
                history.append(
                    {
                        "role": "system",
                        "content": "WARNING: You are nearing the maximum step limit. Please finalize your work and provide a conclusion in the next 1-2 turns.",
                    },
                )

            full_payload = self._inject_clipboard(history=history)

            # Call LLM for response
            # Allow caller to override the streaming and callbacks for displaying chunks, but default to the callbacks aassigned to the agent at creation time
            stream = stream if stream is not None else self.stream
            content_chunk_callbacks = content_chunk_callbacks or self.content_chunk_callbacks
            reasoning_chunk_callbacks = reasoning_chunk_callbacks or self.reasoning_chunk_callbacks

            if debug:
                self._log_debug_messages(full_payload, turn)
            llm_response = await get_llm_response(
                llm_model_config=self.llm_model_config,
                provider_config=self.provider_config,
                messages=full_payload,
                stream=stream if stream is not None else self.stream,
                content_chunk_callbacks=content_chunk_callbacks,
                reasoning_chunk_callbacks=reasoning_chunk_callbacks,
                tools=self._get_tool_definitions() if self.tools else None,
            )

            # 4. Store Assistant Response in memory
            # If there are tool calls, LiteLLM/OpenAI requires they be stored in the history
            assistant_msg = self._create_llm_message(
                role="assistant",
                content=llm_response.content,
                reasoning_content=llm_response.reasoning_content,
            )
            if llm_response.tool_calls:
                # Convert our schema back to the format LiteLLM expects for history
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function_name, "arguments": tc.arguments},
                    }
                    for tc in llm_response.tool_calls
                ]

            self.memory.append_memory(assistant_msg)

            # 5. Check if we need to call tools
            if not llm_response.tool_calls:
                # No more tools? Return the final text
                self.memory.agent_clipboard.last_turn_at = datetime.now(ZoneInfo("UTC"))
                self.update_context_tokens()
                return llm_response.content

            # --- LOOP DETECTION LOGIC ---
            # Stopping the weak model from calling the same tool again and again
            # This heuristic is still not very smart. To be improved in the future
            # Create a hashable signature of current tool calls
            current_calls_signature = sorted(
                [(tc.function_name, tc.arguments) for tc in llm_response.tool_calls],
            )

            # Check if this exact set of tool calls has been made repeatedly
            if tool_call_history and current_calls_signature == tool_call_history[-1]:
                repeat_count = (
                    sum(1 for x in reversed(tool_call_history) if x == current_calls_signature) + 1
                )
                if repeat_count >= max_repetitions:
                    # Naive solution: just stop the agent loop for now. We will find a more elegant handling in the future
                    self.memory.agent_clipboard.last_turn_at = datetime.now(ZoneInfo("UTC"))
                    self.update_context_tokens()
                    return f"Agent terminated: Detected a loop in tool calls ({llm_response.tool_calls[0].function_name})."

            tool_call_history.append(current_calls_signature)

            # 6. Execute Tools in Parallel
            tool_tasks = []
            for tc in llm_response.tool_calls:
                args = json.loads(tc.arguments)
                # Call back to notify tool call starting
                if tool_start_callback:
                    tool_start_cb = [cb(tc.function_name, args) for cb in tool_start_callback]
                    await asyncio.gather(*tool_start_cb)

                tool_tasks.append(
                    self._execute_tool_and_format(tc.id, tc.function_name, args, current_working_directory),
                )

            # Wait for all tool side-effects to finish
            tool_results = await asyncio.gather(*tool_tasks)

            # Add results to history and LOOP BACK
            for res_msg in tool_results:
                self.memory.append_memory(res_msg)
                # Call back to notify tool call results
                if tool_result_callback:
                    tool_start_cb = [
                        cb(res_msg["name"], {"result": res_msg["content"]}) for cb in tool_result_callback
                    ]
                    await asyncio.gather(*tool_start_cb)

        self.memory.agent_clipboard.last_turn_at = datetime.now(ZoneInfo("UTC"))
        self.update_context_tokens()
        return "Agent reached maximum allowed turns without reaching a conclusion."

    async def add_file(self, file_path: Path, working_directory: Path | None = None):
        """Method for external workflows to feed files to the agent."""
        # 1. Path Validation
        current_working_directory = self._get_current_working_directory(working_directory)
        logical_path = Path(os.path.normpath(current_working_directory / file_path))
        print(f"CURRENT WORKING DIRECTORY {current_working_directory}")
        print(f"RESOLVED PATH {logical_path}")

        if not logical_path.is_relative_to(current_working_directory.resolve()):
            raise ValueError(f"Security Alert: Path {file_path} is outside of {current_working_directory}")

        if not logical_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 2. Determine File Type
        extension = logical_path.suffix.lower()

        content = ""
        safe_file_path = logical_path.relative_to(current_working_directory)
        extension = logical_path.suffix.lower()

        # 1. Handle Known Non-Text Formats first
        if extension == ".pdf":
            return await asyncio.to_thread(
                convert_pdf_to_markdown,
                pdf_path=logical_path,
                prune_references=True,
            )

        # List of extensions to explicitly ignore (binaries/assets)
        # This prevents wasting IO on large images or compiled files
        BINARY_EXTENSIONS = {
            ".exe",
            ".bin",
            ".pyc",
            ".o",
            ".obj",
            ".dll",
            ".so",
            ".dylib",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".webp",
            ".mp3",
            ".mp4",
            ".wav",
            ".avi",
            ".mov",
            ".zip",
            ".tar",
            ".gz",
            ".7z",
            ".docx",
            ".xlsx",
            ".pptx",
            ".sqlite",
            ".db",
        }

        if extension in BINARY_EXTENSIONS:
            raise ValueError(f"Unsupported binary file type: {extension}")

        # 2. Heuristic: Check if the file is binary or text
        def is_text_and_read():
            # Check first 1024 bytes for null character
            with open(logical_path, "rb") as f:
                chunk = f.read(1024)
                if b"\0" in chunk:
                    return None  # It's a binary file

            # If no null byte, attempt to read as text
            try:
                with open(logical_path, encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                return None

        content = await asyncio.to_thread(is_text_and_read)
        if content is None:
            raise ValueError(f"File {logical_path.name} appears to be binary or unreadable.")

        # 4. Add to Memory
        self.memory.add_file_to_clipboard(safe_file_path, content)

    async def remove_files(self, path: Path, working_directory: Path | None = None) -> list[Path]:
        """Method for external workflows to remove files from the agent's clipboard
        Return a list of Path of files removed
        """
        # Path Validation
        current_working_directory = self._get_current_working_directory(working_directory)
        resolved_path = path.resolve()

        if not resolved_path.is_relative_to(current_working_directory.resolve()):
            raise ValueError(
                f"Security Alert: Path to remove {path} is outside of {current_working_directory}",
            )

        if not resolved_path.exists():
            raise FileNotFoundError(f"Given path not found: {path}")

        safe_path = resolved_path.relative_to(current_working_directory)

        if safe_path.is_file():
            if self.memory.remove_file_from_clipboard(safe_path):
                return [safe_path]

        if safe_path.is_dir():
            return self.memory.remove_dir_from_clipboard(safe_path)

        return []

    def get_clipboard(self):
        return self.memory.get_clipboard_message(timezone=self.timezone)

    def update_context_tokens(self):
        """Update stored token counts on memory by asking memory."""
        self.memory.history_tokens = self.memory.count_history_tokens(self.llm_model_config.model)
        self.memory.clipboard_tokens = self.memory.count_clipboard_tokens(self.llm_model_config.model)

    def get_context_info(self) -> dict[str, Any]:
        """Return context token breakdown for external consumers."""
        history = self.memory.history_tokens
        clipboard = self.memory.clipboard_tokens
        total = history + clipboard
        max_tok = self.max_context_tokens
        percent = round(total / max_tok * 100, 1) if max_tok else 0.0
        return {
            "history_tokens": history,
            "clipboard_tokens": clipboard,
            "total_tokens": total,
            "max_tokens": max_tok,
            "percent": percent,
        }


async def main():
    settings = get_config()
    [llm_model, llm_provider] = settings.default_llm_config
    agent_config = AgentConfig(name="my-test-agent", llm_config=llm_model, provider_config=llm_provider)
    agent = Agent(
        agent_config=agent_config,
        timezone=settings.timezone,
        content_chunk_callbacks=[streamcallback_simple_print],
        reasoning_chunk_callbacks=[streamcallback_simple_print],
        working_directory=settings.path.working_directory,
    )

    print(
        f"Turn 1:\n{await agent.step('hello, how are you?', working_directory=Path(__file__).parent)}\n-----",
    )

    await agent.add_file(Path(__file__).resolve())

    print(f"Turn 2:\n{await agent.step('Can you explain to me the file in the clipboard?')}\n-----")

    messages = agent.memory.get_messages()
    print(f"\n\nAll of the messages:\n{messages}")


if __name__ == "__main__":
    asyncio.run(main())
