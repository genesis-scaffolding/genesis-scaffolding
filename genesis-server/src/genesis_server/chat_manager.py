import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ActiveRun:
    def __init__(self, session_id: int, user_input: str):
        self.session_id = session_id
        # Index 0 is always the User input
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": user_input}]
        self.clients: list[asyncio.Queue] = []

    def _get_or_create_assistant_message_index(self) -> int:
        """Returns the index of the current assistant message.
        If the last message isn't an assistant message (e.g. it's a tool response),
        it appends a new assistant message.
        """
        if not self.messages or self.messages[-1]["role"] != "assistant":
            self.messages.append(
                {"role": "assistant", "content": "", "reasoning_content": "", "tool_calls": []},
            )
        return len(self.messages) - 1

    async def _broadcast(self, event: str, data: Any, index: int | None = None):
        payload = {
            "event": event,
            "data": data,
            "index": index,  # The frontend uses this to target the right message
        }
        for q in self.clients:
            await q.put(payload)

    # --- Callbacks ---

    async def handle_reasoning(self, chunk: str):
        idx = self._get_or_create_assistant_message_index()
        self.messages[idx]["reasoning_content"] += chunk
        await self._broadcast("reasoning", chunk, index=idx)

    async def handle_content(self, chunk: str):
        idx = self._get_or_create_assistant_message_index()
        self.messages[idx]["content"] += chunk
        await self._broadcast("content", chunk, index=idx)

    async def handle_tool_start(self, name: str, args: dict):
        idx = self._get_or_create_assistant_message_index()
        tool_call = {"name": name, "args": args, "status": "running"}
        self.messages[idx]["tool_calls"].append(tool_call)

        # We broadcast the tool_start for the UI to show a "Loading" state
        # We include the index of the assistant message that owns this tool call
        await self._broadcast("tool_start", {"name": name, "args": args}, index=idx)

    async def handle_tool_result(self, name: str, args: dict):
        # 1. Update the 'running' status in the parent assistant message
        # We look for the assistant message that just called this tool
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]["role"] == "assistant":
                for tc in self.messages[i]["tool_calls"]:
                    if tc["name"] == name:
                        tc["status"] = "completed"
                break

        # 2. Append the NEW 'tool' role message to the list
        tool_msg = {"role": "tool", "name": name, "content": args.get("result", "")}
        self.messages.append(tool_msg)
        new_idx = len(self.messages) - 1

        # 3. Broadcast. The frontend sees a new index and knows it's a tool result message.
        await self._broadcast("tool_result", tool_msg, index=new_idx)

    async def handle_token_usage(self, context_info: dict):
        """Called after DB persistence to broadcast token usage to all SSE clients."""
        await self._broadcast("token_usage", context_info)

    async def handle_clipboard(self, clipboard_md: str):
        """Broadcast clipboard markdown snapshot to all SSE clients after agent step."""
        await self._broadcast("clipboard", {"clipboard_md": clipboard_md})

    def add_client(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.clients.append(q)
        return q

    def remove_client(self, q: asyncio.Queue):
        if q in self.clients:
            self.clients.remove(q)


class ChatManager:
    """Global manager for all active agent runs."""

    def __init__(self):
        self.active_runs: dict[int, ActiveRun] = {}
        logger.debug("ChatManager initialized with empty active_runs")

    def get_or_create_run(self, session_id: int, user_input: str) -> ActiveRun:
        if session_id not in self.active_runs:
            logger.info("Creating new ActiveRun for session_id=%d", session_id)
            self.active_runs[session_id] = ActiveRun(session_id, user_input=user_input)
        else:
            logger.debug("Reusing existing ActiveRun for session_id=%d", session_id)
        return self.active_runs[session_id]

    def clear_run(self, session_id: int):
        if session_id in self.active_runs:
            # Signal end of stream to any lingering clients
            run = self.active_runs[session_id]
            for q in run.clients:
                q.put_nowait(None)
            logger.info("Cleared ActiveRun for session_id=%d", session_id)
            del self.active_runs[session_id]
        else:
            logger.debug("clear_run called with session_id=%d but no active run exists", session_id)
