# Agent Clipboard Architecture

One of the experimental optimizations in this project is a feature called the **"clipboard."** The goal is to optimize the number of tokens an LLM agent uses. Lower token consumption means the agent can maintain coherence over longer sessions without hitting context limits.

## The Problem: How Agents Handle Context

Working with an LLM is basically about getting the "right" text into the context window to get the "right" output. When an agent needs to summarize or compare documents, those documents have to be stuffed into the context somehow.

In an "agentic" approach, the LLM calls a tool to request a file. While this is the most flexible method, it’s often inefficient for a few reasons:

### 1. Sub-optimal reading decisions
Agents often make mistakes about what to read. For example, if you ask an agent to create a React component based on a backend Pydantic model, it needs to see the model, the utility code, and some existing components for reference.

If you did this manually, you’d paste exactly those files and use a few thousand tokens. An agent, however, might:
*   Bring in irrelevant files because it misunderstood the directory structure.
*   Read the same file multiple times if a previous edit failed.
*   Read a file in small, overlapping chunks, wasting tokens on redundant text.

This "gunk" builds up. Suddenly, a 128k context window isn't enough for a task that should only require a few thousand tokens.

### 2. Accumulation of outdated content
If an agent modifies a file three times, the chat history often ends up containing three slightly different versions of that same file. This is a massive waste of space.

### 3. Misleading the models
We tend to think of agents as having a "memory" of the past, but LLMs are stateless. Every time you wake them up, they see the entire history as one long string. Irrelevant files or multiple outdated versions of the same code dilute the context and confuse the model, leading to "context rot" and lower performance.

**Summary:** Naive agentic reading (storing every file read directly in the chat history) is impractical. It requires expensive SOTA models to handle the mess, whereas a cleaner context could be handled by smaller, faster models.

---

## The Clipboard Mechanism

The clipboard is designed to replace naive file reading. It aims to:
*   Stop the accumulation of outdated/duplicate content.
*   Automatically "forget" unused information.
*   Keep tool call sequences compatible with LLM providers.
*   **Preserve prompt caching** (prefix caching), which keeps the agent fast and cheap.

### How it works
Every agent has a "clipboard"—essentially a bag of data managed by the software harness. 

When the agent calls a file-reading tool, the content doesn't go into the chat history. Instead, it goes into the **clipboard**. The tool response sent to the LLM is just a "receipt" confirming the file was read. 

Before the harness sends a message to the LLM, it injects the current clipboard content as a system message. 

**Key features:**
*   **Deduplication:** If an agent reads the same file again, the clipboard entry is updated rather than duplicated.
*   **TTL (Time To Live):** Every item on the clipboard has a TTL that decreases every turn. When it hits zero, the item is removed ("forgotten").
*   **Cache Friendly:** Because we only append to the message history and don't modify previous messages, we don't break the LLM provider's prompt caching.

### Clipboard Content Types
The clipboard currently tracks four things:
1.  **Todo list:** A list of tasks to keep the agent on track without repeating them in history.
2.  **Accessed Files:** A dictionary of file contents (keyed by path to prevent duplicates).
3.  **Tool Results:** Results of specific tool calls.
4.  **Current Date and Time:** To keep the agent oriented.

---

## Implementation Details

The clipboard logic lives in the `myproject-core` package.

### Schemas (`schemas.py`)
These models define how data is stored and how long it stays there.

```python
class AgentClipboardFile(BaseModel):
    file_path: Path
    file_content: str
    ttl: int = 10  # Stays for 10 turns by default

class AgentClipboardToolResult(BaseModel):
    tool_name: str
    tool_call_id: str
    tool_call_results: list[str]
    ttl: int = 10

class AgentClipboardTodoItem(BaseModel):
    completed: bool = False
    task_desc: str

class AgentClipboard(BaseModel):
    accessed_files: dict[str, AgentClipboardFile] = {}
    tool_results: dict[str, AgentClipboardToolResult] = {}
    todo_list: list[AgentClipboardTodoItem] = []
```

### Memory Management (`agent_memory.py`)
The `AgentMemory` class manages the chat history and the clipboard. The `get_clipboard_message` method turns the clipboard into a temporary system message.

```python
class AgentMemory:
    def forget(self):
        """Reduces TTL and removes expired items."""
        self.agent_clipboard.reduce_ttl()
        self.agent_clipboard.remove_expired_items()

    def get_clipboard_message(self) -> dict[str, str]:
        """Formats the clipboard as an ephemeral system message."""
        content = (
            "## CURRENT CLIPBOARD\n"
            f"{self.agent_clipboard.render_to_markdown()}\n"
            "## CURRENT DATE TIME\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return {"role": "system", "content": content}
```

### The Agent Loop (`agent.py`)
The agent injects the clipboard into the payload right before calling the LLM. After the LLM responds, the history remains "clean" because the clipboard message was never saved to the permanent history—only the result of the LLM's turn is.

```python
# Inside the agent's step loop:
history = self.memory.get_messages()
past_history = history[:-1]
latest_query = history[-1:]
clipboard_context = [self.memory.get_clipboard_message()]

# Inject clipboard before the latest user message
full_payload = past_history + clipboard_context + latest_query

llm_response = await get_llm_response(messages=full_payload, ...)
```

When a tool like `read_file` is executed, the `_execute_tool_and_format` helper handles the side effect of updating the clipboard:

```python
if result.status == "success" and result.files_to_add_to_clipboard:
    for file_path in result.files_to_add_to_clipboard:
        await self.add_file(file_path=file_path) # Updates clipboard
```
