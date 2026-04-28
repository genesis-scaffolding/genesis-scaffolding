"""
AgentEngine for genesis_core.

Encapsulates the wiring logic previously in genesis_server/routers/chat.py:
- Reconstructing AgentMemory from DB
- Truncating history for message editing
- Creating agent via agent_registry
- Wiring callbacks to EventBus
- Running agent.step()
- Persisting new messages via chat_manager
- Broadcasting final token/clipboard state
"""

import logging
from datetime import UTC, datetime

from ..configs import Config
from ..events import CoreEvent, CoreEventType, EventBus
from ..managers.chat import ChatSessionManager
from .agent_memory import AgentMemory
from .agent_registry import AgentRegistry
from .clipboard import AgentClipboard

logger = logging.getLogger(__name__)


class AgentEngine:
    """Engine for running agent steps with full lifecycle management."""

    def __init__(
        self,
        config: Config,
        agent_registry: AgentRegistry,
        chat_manager: ChatSessionManager,
    ):
        self.config = config
        self.agent_registry = agent_registry
        self.chat_manager = chat_manager

    async def run(
        self,
        session_id: int,
        user_input: str,
        event_bus: EventBus,
        edit_index: int | None = None,
    ) -> None:
        """
        Full agent lifecycle:

        1. Load chat session from chat_manager
        2. Reconstruct AgentMemory from messages + clipboard
        3. Create agent via agent_registry
        4. Wire callbacks to event_bus
        5. Run agent.step()
        6. Persist new messages via chat_manager
        7. Broadcast final token/clipboard state
        """
        user_id = self._get_user_id_from_session(session_id)
        if user_id is None:
            raise ValueError(f"Session {session_id} not found or access denied")

        # 1. Load session and messages
        chat_session = self.chat_manager.get_session(session_id, user_id)
        if not chat_session:
            raise ValueError(f"Session {session_id} not found")

        past_messages = self.chat_manager.get_messages(session_id, user_id)
        messages_list = [m.payload for m in past_messages]

        # 2. Truncate history if editing
        if edit_index is not None and edit_index < 0:
            user_messages_with_records = [
                (i, record) for i, record in enumerate(past_messages) if record.payload.get("role") == "user"
            ]
            user_indices = [i for i, _ in user_messages_with_records]

            try:
                target_idx = user_indices[edit_index]
            except IndexError as err:
                raise ValueError("Cannot edit: message index out of range") from err

            # Build list of (index, record) pairs for user messages only
            messages_list = messages_list[:target_idx]

            # Delete messages from DB in same transaction
            # (handled separately via chat_manager)

        # 3. Reconstruct AgentMemory
        clipboard = (
            AgentClipboard.model_validate(chat_session.clipboard_state)
            if chat_session.clipboard_state
            else None
        )
        if messages_list or clipboard:
            memory = AgentMemory(messages=messages_list, agent_clipboard=clipboard)
        else:
            memory = None

        # 4. Create agent
        agent = self.agent_registry.create_agent(
            chat_session.agent_id,
            working_directory=self.config.path.working_directory,
            memory=memory,
        )

        # 5. Record initial length to know which messages are new
        initial_memory_length = len(agent.memory.messages)

        # 6. Wire callbacks to event_bus
        async def content_cb(chunk: str):
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_CONTENT,
                session_id=session_id,
                data={"chunk": chunk},
            ))

        async def reasoning_cb(chunk: str):
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_REASONING,
                session_id=session_id,
                data={"chunk": chunk},
            ))

        async def tool_start_cb(name: str, args: dict):
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_TOOL_START,
                session_id=session_id,
                data={"name": name, "args": args},
            ))

        async def tool_result_cb(name: str, args: dict):
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_TOOL_RESULT,
                session_id=session_id,
                data={"name": name, "result": args.get("result", "")},
            ))

        # 7. Run agent step
        await agent.step(
            input=user_input,
            stream=True,
            content_chunk_callbacks=[content_cb],
            reasoning_chunk_callbacks=[reasoning_cb],
            tool_start_callback=[tool_start_cb],
            tool_result_callback=[tool_result_cb],
        )

        # 8. Persist new messages
        new_messages = agent.memory.messages[initial_memory_length:]
        if new_messages:
            self.chat_manager.add_messages(session_id, user_id, new_messages)

        # 9. Update clipboard state and timestamp
        self.chat_manager.update_clipboard_state(
            session_id,
            user_id,
            agent.memory.agent_clipboard.model_dump(mode="json") if agent.memory and agent.memory.agent_clipboard else {},
        )
        self.chat_manager.update_session(session_id, user_id, is_running=False, updated_at=datetime.now(UTC))

        # 10. Broadcast final token usage
        context_info = agent.get_context_info()
        await event_bus.publish(CoreEvent(
            event_type=CoreEventType.AGENT_TOKEN_USAGE,
            session_id=session_id,
            data=context_info,
        ))

        # 11. Broadcast clipboard snapshot
        if agent.memory and agent.memory.agent_clipboard:
            clipboard_md = agent.memory.agent_clipboard.render_to_markdown()
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_CLIPBOARD_SNAPSHOT,
                session_id=session_id,
                data={"clipboard_md": clipboard_md},
            ))

        logger.info("AgentEngine: session %s completed", session_id)

    def _get_user_id_from_session(self, session_id: int) -> int | None:
        """Quick helper to get user_id from a session without full load."""
        return self.chat_manager.get_user_id_from_session(session_id)
