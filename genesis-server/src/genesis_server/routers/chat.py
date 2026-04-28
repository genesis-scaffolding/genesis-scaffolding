"""
Chat router using EventBus for SSE streaming.

All DB operations go through core.chat_manager.
Agent execution goes through core.agent_engine.
SSE streaming uses EventBus: router creates a bus per session,
SSE clients subscribe to it.
"""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from genesis_core.events import CoreEvent, CoreEventType, EventBus

from genesis_server.dependencies import CoreDep, InboxDep
from genesis_server.schemas.chat import ChatSessionCreate

router = APIRouter(prefix="/chats", tags=["chats"])
logger = logging.getLogger(__name__)


# GET ALL CHAT SESSIONS
@router.get("/")
async def list_sessions(core: CoreDep):
    """List all chat sessions for the current user."""
    return core.list_chat_sessions()


# CREATE NEW SESSION
@router.post("/", response_model=dict)
async def create_session(
    payload: ChatSessionCreate,
    core: CoreDep,
    inbox: InboxDep,
):
    """Create a new chat session with an agent."""
    agent_id = payload.agent_id

    # Validate agent exists
    if agent_id not in core.agent_registry.get_all_agent_types():
        raise HTTPException(status_code=404, detail="Agent not found")

    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    # Get initial messages from agent (system prompt, greeting, etc.)
    agent = core.agent_registry.create_agent(agent_id, working_directory=inbox)
    initial_messages = agent.memory.get_messages() if hasattr(agent, 'memory') and agent.memory else []

    # Create session with initial messages
    session = core.chat_manager.create_session(
        user_id=user_id,
        agent_id=agent_id,
        title=payload.title or "New Chat",
        initial_messages=[{"role": m.get("role"), "content": m.get("content")} for m in initial_messages] if initial_messages else None,
    )
    return session


# GET SESSION HISTORY
@router.get("/{session_id}", response_model=dict)
async def get_chat_history(
    session_id: int,
    core: CoreDep,
):
    """Get session with messages and context info."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    try:
        session, messages = core.get_chat_session(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found") from None

    return {
        "session": session,
        "messages": messages,
        "context_tokens": {},  # TODO: wire token counting via agent engine
    }


@router.post("/{session_id}/message")
async def send_message(
    session_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    core: CoreDep,
    input_index: int | None = None,
    user_input: str = Body(..., embed=True),
):
    """Run an agent turn on a chat session. Streams events via SSE."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    logger.info(
        "(Chat Session %s) Received new message from user\n- user_input: %s\n- input_index: %s",
        session_id,
        user_input,
        input_index,
    )

    # Validate input_index
    if input_index is not None and input_index > 0:
        raise HTTPException(status_code=400, detail="input_index must be negative or zero")

    # Load session to verify ownership
    session_obj = core.chat_manager.get_session(session_id, user_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check concurrency lock
    if session_obj.is_running:
        raise HTTPException(status_code=409, detail="Agent is currently processing a message.")

    # Handle message editing: truncate history to the target user message
    if input_index is not None and input_index < 0:
        past_messages = core.chat_manager.get_messages(session_id, user_id)
        user_messages_with_records = [
            (i, record) for i, record in enumerate(past_messages)
            if record.payload.get("role") == "user"
        ]
        user_indices = [i for i, _ in user_messages_with_records]
        try:
            target_idx = user_indices[input_index]
        except IndexError:
            raise HTTPException(status_code=400, detail="Cannot edit: message index out of range") from None

        target_record = past_messages[target_idx]
        # Delete messages from target onwards
        if target_record.id is not None:
            core.chat_manager.delete_messages_after(session_id, user_id, target_record.id)

    # Lock session
    core.chat_manager.update_session(session_id, user_id, is_running=True)

    # Create EventBus for this run and store in app.state
    event_bus = EventBus()
    if not hasattr(request.app.state, 'chat_streams'):
        request.app.state.chat_streams = {}
    request.app.state.chat_streams[session_id] = event_bus

    # Background task
    async def run_agent():
        try:
            await core.agent_engine.run(session_id, user_input, event_bus, edit_index=input_index)
        except Exception as e:
            logger.error("Agent error for session %s: %s", session_id, e)
            await event_bus.publish(CoreEvent(
                event_type=CoreEventType.AGENT_CONTENT,
                session_id=session_id,
                data={"chunk": f"[Error: {e!s}]"},
            ))
        finally:
            event_bus.done()
            # Clean up stream reference
            if hasattr(request.app.state, 'chat_streams') and session_id in request.app.state.chat_streams:
                del request.app.state.chat_streams[session_id]

    background_tasks.add_task(run_agent)
    return {"status": "accepted", "message": "Agent is thinking..."}


@router.get("/{session_id}/stream")
async def stream_chat(
    session_id: int,
    request: Request,
    core: CoreDep,
):
    """SSE stream for chat session events."""
    user_id = core.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="User has no ID")

    # Verify session access
    session_obj = core.chat_manager.get_session(session_id, user_id)
    if not session_obj:
        raise HTTPException(status_code=404)

    if not hasattr(request.app.state, 'chat_streams') or session_id not in request.app.state.chat_streams:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    event_bus = request.app.state.chat_streams[session_id]

    async def event_generator():
        # Get catchup: current messages from the session
        try:
            _, messages = core.get_chat_session(session_id)
            interim = [{"role": m.payload.get("role"), "content": m.payload.get("content")} for m in messages]
            yield f"event: catchup\ndata: {json.dumps({'interim_messages': interim})}\n\n"
        except ValueError:
            pass

        # Stream events from EventBus
        async for event in event_bus.subscribe():
            if event.event_type == CoreEventType.AGENT_CONTENT:
                yield f"event: content\ndata: {json.dumps({'chunk': event.data.get('chunk', '')})}\n\n"
            elif event.event_type == CoreEventType.AGENT_REASONING:
                yield f"event: reasoning\ndata: {json.dumps({'chunk': event.data.get('chunk', '')})}\n\n"
            elif event.event_type == CoreEventType.AGENT_TOOL_START:
                yield f"event: tool_start\ndata: {json.dumps({'name': event.data.get('name', ''), 'args': event.data.get('args', {})})}\n\n"
            elif event.event_type == CoreEventType.AGENT_TOOL_RESULT:
                yield f"event: tool_result\ndata: {json.dumps({'name': event.data.get('name', ''), 'result': event.data.get('result', '')})}\n\n"
            elif event.event_type == CoreEventType.AGENT_TOKEN_USAGE:
                yield f"event: token_usage\ndata: {json.dumps(event.data)}\n\n"
            elif event.event_type == CoreEventType.AGENT_CLIPBOARD_SNAPSHOT:
                yield f"event: clipboard\ndata: {json.dumps({'clipboard_md': event.data.get('clipboard_md', '')})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
