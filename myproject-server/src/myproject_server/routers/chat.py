import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from myproject_core.agent_memory import AgentMemory
from myproject_core.agent_registry import AgentRegistry
from myproject_core.schemas import AgentClipboard
from sqlmodel import Session, col, select

from ..chat_manager import ChatManager
from ..database import get_session, get_session_context
from ..dependencies import get_agent_registry, get_current_active_user, get_user_inbox_path
from ..models.chat import ChatMessage, ChatSession
from ..models.user import User
from ..schemas.chat import ChatHistoryRead, ChatSessionCreate, ChatSessionRead

router = APIRouter(prefix="/chats", tags=["chats"])


# GET ALL CHAT SESSIONS
@router.get("/", response_model=list[ChatSessionRead])
async def list_sessions(
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_current_active_user)],
    agent_reg: Annotated[AgentRegistry, Depends(get_agent_registry)],
):
    # 1. Get the IDs of all currently available agents from the registry
    # agent_reg.get_all_agent_types() returns the keys (filenames) of existing agents
    active_agent_ids = list(agent_reg.get_all_agent_types())

    # 2. If no agents are registered, return an empty list immediately
    # (prevents SQL errors or unnecessary queries)
    if not active_agent_ids:
        return []

    # 3. Filter the query so it only returns sessions where the agent_id
    # is still in the registry
    return db.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user.id, col(ChatSession.agent_id).in_(active_agent_ids))
        .order_by(col(ChatSession.updated_at).desc()),
    ).all()


# 2. CREATE NEW SESSION
@router.post("/", response_model=ChatSessionRead)
async def create_session(
    config: ChatSessionCreate,
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_current_active_user)],
    agent_reg: Annotated[AgentRegistry, Depends(get_agent_registry)],
    working_dir: Annotated[Path, Depends(get_user_inbox_path)],
):
    # 1. Validate agent exists
    if config.agent_id not in agent_reg.get_all_agent_types():
        raise HTTPException(status_code=404, detail="Agent not found")

    if not user.id:
        raise HTTPException(status_code=400, detail="User not found")

    # 2. Create the Session object
    new_session = ChatSession(user_id=user.id, agent_id=config.agent_id, title=config.title or "New Chat")

    db.add(new_session)
    # Flush sends the 'INSERT' to the DB to generate the ID, but doesn't commit the transaction yet
    db.flush()

    if not new_session.id:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create session")

    # 3. Initialize Agent to get starting messages (System prompts, greetings, etc.)
    agent = agent_reg.create_agent(config.agent_id, working_directory=working_dir)
    agent_messages = agent.memory.get_messages()

    # 4. Add initial messages to the database
    for msg in agent_messages:
        db_msg = ChatMessage(
            session_id=new_session.id,  # Use the ID generated during flush
            payload=msg,
        )
        db.add(db_msg)

    # 5. Commit all changes at once
    try:
        db.commit()
        db.refresh(new_session)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e!s}")

    return new_session


# 3. GET SESSION HISTORY
@router.get("/{session_id}", response_model=ChatHistoryRead)
async def get_chat_history(
    session_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_active_user),
):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404)

    messages = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(col(ChatMessage.id).asc()),
    ).all()

    return {"session": session, "messages": messages}


@router.post("/{session_id}/message")
async def send_message(
    session_id: int,
    user_input: str,
    background_tasks: BackgroundTasks,
    request: Request,
    working_dir: Annotated[Path, Depends(get_user_inbox_path)],
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_current_active_user)],
    agent_reg: AgentRegistry = Depends(get_agent_registry),
):
    # 1. Fetch Session
    chat_session = db.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Concurrency Lock: Check if already running
    if chat_session.is_running:
        raise HTTPException(status_code=409, detail="Agent is currently processing a message.")

    # 3. Reconstruct AgentMemory
    past_messages = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(col(ChatMessage.id).asc()),
    ).all()

    memory_list = [m.payload for m in past_messages]

    clipboard = (
        AgentClipboard.model_validate(chat_session.clipboard_state)
        if chat_session.clipboard_state
        else None
    )
    # This is crucial to fix a bug where the agent is initialized with empty messages list
    # Thus losing the system prompt
    if memory_list and clipboard:
        memory = AgentMemory(messages=memory_list, agent_clipboard=clipboard)
    else:
        memory = None

    # 4. Get Agent & Initialize Run
    agent = agent_reg.create_agent(chat_session.agent_id, working_directory=working_dir, memory=memory)

    chat_manager: ChatManager = (
        request.app.state.chat_manager
    )  # Assuming we add this to app.state in lifespan
    active_run = chat_manager.get_or_create_run(session_id, user_input=user_input)

    # 5. Define Background Execution
    async def run_agent_task():
        try:
            # We record the length to know exactly which messages are "new"
            initial_memory_length = len(agent.memory.messages)

            # print("AGENT MEMORY BEFORE CALLING STEP")
            # print(agent.memory.get_messages())
            # print(initial_memory_length)
            # Execution with callbacks!
            await agent.step(
                input=user_input,
                stream=True,
                content_chunk_callbacks=[active_run.handle_content],
                reasoning_chunk_callbacks=[active_run.handle_reasoning],
                tool_start_callback=[active_run.handle_tool_start],
                tool_result_callback=[active_run.handle_tool_result],
            )

            # --- POST RUN PERSISTENCE ---
            # Extract only the newly generated messages (user message + agent responses + tools)
            new_messages = agent.memory.messages[initial_memory_length:]

            # print("NEW MESSAGES TO WRITE TO DATABASE")
            # print(new_messages)
            # We need a fresh DB session for the background task
            with get_session_context() as bg_db:  # Assuming you have a context manager for DB
                session_to_update = bg_db.get(ChatSession, session_id)
                if session_to_update:
                    # Save new messages
                    for msg in new_messages:
                        db_msg = ChatMessage(session_id=session_id, payload=msg)
                        bg_db.add(db_msg)

                    # Save clipboard, update timestamp, and unlock
                    session_to_update.clipboard_state = agent.memory.agent_clipboard.model_dump(mode="json")
                    session_to_update.updated_at = datetime.now(UTC)
                    session_to_update.is_running = False
                    bg_db.commit()

        except Exception as e:
            # Handle error, unlock DB
            print(f"Agent Error: {e}")
            with get_session_context() as bg_db:
                session_to_update = bg_db.get(ChatSession, session_id)
                if session_to_update:
                    session_to_update.is_running = False
                    bg_db.add(session_to_update)
                    bg_db.commit()
        finally:
            chat_manager.clear_run(session_id)

    # 6. Dispatch to background and return 202
    background_tasks.add_task(run_agent_task)
    # Lock it in DB
    chat_session.is_running = True
    db.commit()
    return {"status": "accepted", "message": "Agent is thinking..."}


@router.get("/{session_id}/stream")
async def stream_chat(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_active_user),
):
    # Standard validation
    chat_session = db.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != user.id:
        raise HTTPException(status_code=404)

    chat_manager: ChatManager = request.app.state.chat_manager
    if session_id not in chat_manager.active_runs:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    active_run = chat_manager.active_runs[session_id]
    client_queue = active_run.add_client()

    async def event_generator():
        try:
            # 1. Send the CATCHUP payload
            # This contains all messages (User, Assistant, Tool) produced in THIS step
            yield f"event: catchup\ndata: {json.dumps({'interim_messages': active_run.messages})}\n\n"

            # 2. Live stream subsequent chunks
            while True:
                if await request.is_disconnected():
                    break

                item = await client_queue.get()
                if item is None:
                    break

                payload = {"data": item["data"], "index": item.get("index")}
                yield f"event: {item['event']}\ndata: {json.dumps(payload)}\n\n"
        finally:
            active_run.remove_client(client_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
