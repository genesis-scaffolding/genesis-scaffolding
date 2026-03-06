# Tool Architecture

This project uses tool calls to extend LLM agent functionality. The workflow follows the standard pattern used by most modern agent implementations:

1.  **Schema Sharing:** A list of tool schemas is sent to the LLM provider.
2.  **Model Decision:** The LLM decides to call a tool and generates a structured request (JSON/XML).
3.  **Harness Execution:** The agent harness parses the request and executes the corresponding Python code using the provided parameters.
4.  **Feedback Loop:** The harness sends the result (or error) back to the LLM. The LLM then decides to either call another tool or provide a final response.

### The Key Difference: Multi-Channel Results

Usually, tool results are just text placed directly into the chat history. In this design, a tool can return data to the agent in three specific ways:
1.  **Tool response text:** The standard message sent back to the LLM's chat history.
2.  **Clipboard text:** Specific text content to be added to the agent's internal clipboard.
3.  **Files to clipboard:** A list of file paths that the system will read and add to the clipboard.

---

## Implementation Details

Tools are built using the `myproject-tools` package. Every tool must be a Python object inheriting from the `BaseTool` class in `myproject_tools.base`.

```python
class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def run(self, working_directory: Path, *args: Any, **kwargs: Any) -> ToolResult:
        """Execute logic and return a ToolResult data object."""
        pass

    def to_llm_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
```

**Note on `working_directory`:** The agent harness passes this path to the tool automatically. This allows the same tool (like a file seeker) to work across different environments, whether it’s a local CLI or a remote server sandbox.

### The ToolResult Schema
The output format is defined in `myproject_tools.schema`:

```python
class ToolResult(BaseModel):
    status: Literal["success", "error"]

    # The three output channels
    tool_response: str  # Main output/error sent to the LLM
    results_to_add_to_clipboard: list[str] | None = None  # Text for the clipboard
    files_to_add_to_clipboard: list[Path] = []  # Files to be read into the clipboard
```

---

## How to Implement a New Tool

### 1. Define Inputs
Decide what parameters your tool needs. Give the tool a clear name and a descriptive "description" so the LLM knows when and how to use it.

### 2. Design the Output
Think about how the agent should receive the data. You don't always have to cram everything into the chat history.
*   **Use the clipboard** if you want the agent to "read" a large chunk of text without cluttering the main chat history.
*   **Use file paths** if your tool writes a file to disk that the agent needs to inspect immediately. The framework will handle locating and reading these files into the clipboard for the next turn.

### 3. Write the Logic
Implement the `async run` function. 
*   **Important:** Don't block the event loop. If your tool performs heavy synchronous tasks or long I/O operations, use `asyncio` to run them in a separate thread.

### Example Tool
Here is a basic implementation of a test tool:

```python
class MockTestTool(BaseTool):
    name = "test_tool"
    description = "A tool for testing success and failure handling."
    parameters = {
        "type": "object",
        "properties": {
            "input_text": {"type": "string"},
            "should_fail": {"type": "boolean"}
        },
    }

    async def run(
        self, working_directory: Path, input_text: str, should_fail: bool = False, **kwargs: Any
    ) -> ToolResult:
        if should_fail:
            raise Exception(f"Simulated crash with input: {input_text}")

        return ToolResult(
            status="success",
            tool_response="Processed input text successfully and added to the clipboard.",
            results_to_add_to_clipboard=[f"Processed: {input_text}"],
        )
```
