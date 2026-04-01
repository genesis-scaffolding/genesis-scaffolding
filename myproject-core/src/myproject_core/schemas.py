from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


### JobContext object to be used by workspace manager
class JobContext:
    """A value object representing an active job session of a workflow
    This is what the agent or workflow logic interacts with.
    """

    def __init__(self, root: Path):
        self.root = root
        self.input = root / "input"
        self.internal = root / "internal"
        self.output = root / "output"

    def __repr__(self) -> str:
        return f"<JobContext {self.root.name}>"


### LLM Configs
class LLMProvider(BaseModel):
    """Configuration for an LLM API provider (e.g., OpenRouter, OpenAI, Anthropic)."""

    name: str | None = "openrouter"
    base_url: str | None = "https://openrouter.ai/api/v1"
    api_key: str = Field(default=...)


class LLMModelConfig(BaseModel):
    """Configuration for a specific model instance.
    'provider' matches a key in the providers dictionary.
    'model' is the actual model string passed to LiteLLM.
    'params' contains extra arguments like temperature, max_tokens, reasoning_effort, etc.
    """

    provider: str
    model: str
    params: dict[str, Any] = Field(default_factory=dict)


### LLM Response Message
class ToolCall(BaseModel):
    id: str
    function_name: str
    arguments: str  # We'll store the raw JSON string here for parsing later


class LLMResponse(BaseModel):
    content: str
    reasoning_content: str
    tool_calls: list[ToolCall] = []


### Callback function for handling LLM response chunk
StreamCallback = Callable[[str], Awaitable[None]]

### Callback function for handling LLM response chunk
ToolCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


### Agent Configs
class AgentConfig(BaseModel):
    # Name of the agent for referring to it in the system
    name: str
    # Nickname of LLM model used by the agent
    # This is mostly to make it easier for human user
    model_name: str | None = None
    # LLM Configuration to be used by this model
    llm_config: LLMModelConfig | None = None
    # LLM Configuration to be used by this model
    provider_config: LLMProvider | None = None
    # Only interactive agent can be used in chat
    interactive: bool = False
    # System prompt for the agent
    system_prompt: str = "You are a helpful AI agent."
    # Description of the agent
    description: str = "An AI Assistant Agent."
    # List of allowed tools
    allowed_tools: list[str] = []
    # List of names of allowed agents for delegation
    allowed_agents: list[str] = []
    # Read-only agents cannot be modified or deleted by user
    read_only: bool = False


### Agent's clipboard content
class AgentClipboardFile(BaseModel):
    # Path to the file
    file_path: Path
    # Content of the file (support textual content only for now)
    current_file_content: str
    previous_file_content: str | None = None
    # How many turns left until the file is removed from clipboard
    ttl: int = 10
    # These flags make it easier to filter and parse
    is_new: bool = False  # Has the file just been added in this turn?
    is_edited: bool = False  # Has the file been modified in this turn?


class AgentClipboardToolResult(BaseModel):
    # Name of the tool
    tool_name: str
    # ID of the tool call returned by LLM backend
    tool_call_id: str
    # Results of tool call returned by the tools defined in myproject-tools
    tool_call_results: list[str]
    # How many turns left until the tool call result is removed from clipboard
    ttl: int = 10


class AgentClipboardTodoItem(BaseModel):
    # Completion status of the task
    completed: bool = False
    # Textual description of the task
    task_desc: str


class AgentClipboardPinnedEntity(BaseModel):
    """Represents a database entity pinned to the clipboard."""

    item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"]
    item_id: int
    resolution: Literal["summary", "detail"]
    ttl: int

    # The actual database record converted to a dictionary.
    # This is updated every turn by the Agent loop (Live-Sync).
    data: dict[str, Any] = {}


class AgentClipboard(BaseModel):
    accessed_files: dict[str, AgentClipboardFile] = {}
    tool_results: dict[str, AgentClipboardToolResult] = {}
    todo_list: list[AgentClipboardTodoItem] = []
    pinned_entities: dict[str, AgentClipboardPinnedEntity] = {}
    memory_tag_hints: dict[str, int] = {}  # tag -> count of current memories

    def add_file_to_clipboard(self, file_path: Path, content: str):
        """Adds or updates a file in the clipboard."""
        if str(file_path) not in self.accessed_files.keys():
            # If the file does not exist in the clipboard, then add it
            new_file = AgentClipboardFile(file_path=file_path, current_file_content=content, is_new=True)
            self.accessed_files[str(file_path)] = new_file
        else:
            # If the file is already in the clipboard, add a new version of the content
            old_file = self.accessed_files[str(file_path)]
            old_file.previous_file_content = old_file.current_file_content
            old_file.current_file_content = content
            old_file.is_new = False
            old_file.is_edited = True

    def add_tool_result_to_clipboard(self, tool_name: str, tool_call_id: str, tool_call_results: list[str]):
        """Add results of tool call to the clipboard"""
        new_tool_result = AgentClipboardToolResult(
            tool_name=tool_name, tool_call_id=tool_call_id, tool_call_results=tool_call_results,
        )
        self.tool_results[tool_call_id] = new_tool_result

    def remove_file_from_clipboard(self, file_path: Path) -> bool:
        """Remove a given file from clipboard
        Return False if file does not exist.
        """
        if str(file_path) in self.accessed_files:
            del self.accessed_files[str(file_path)]
            return True
        return False

    def pin_entity(
        self,
        item_type: Literal["task", "project", "journal", "memory_event", "memory_topic"],
        item_id: int,
        resolution: Literal["summary", "detail"],
        ttl: int = 10,
    ):
        """Adds or updates a pinned entity (productivity or memory)."""
        key = f"{item_type}_{item_id}"
        if key in self.pinned_entities:
            # If it exists, update resolution and reset TTL
            self.pinned_entities[key].resolution = resolution
            self.pinned_entities[key].ttl = ttl
        else:
            self.pinned_entities[key] = AgentClipboardPinnedEntity(
                item_type=item_type, item_id=item_id, resolution=resolution, ttl=ttl,
            )

    def reduce_ttl(self):
        """Reduce ttl of every item stored in clipboard"""
        if self.accessed_files:
            for _, file in self.accessed_files.items():
                file.ttl = file.ttl - 1

        if self.tool_results:
            for _, tool_result in self.tool_results.items():
                tool_result.ttl = tool_result.ttl - 1

        if self.pinned_entities:
            for _, entity in self.pinned_entities.items():
                entity.ttl -= 1
                # DECAY: If an item gets old (e.g., <= 5 turns left), downgrade it to save tokens
                if entity.ttl <= 5 and entity.resolution == "detail":
                    entity.resolution = "summary"

    def remove_expired_items(self):
        """Remove expired files and tool call results"""
        # Reconstruct the dictionaries keeping only items with ttl > 0
        self.accessed_files = {key: file for key, file in self.accessed_files.items() if file.ttl > 0}
        self.tool_results = {key: result for key, result in self.tool_results.items() if result.ttl > 0}
        self.pinned_entities = {
            key: entity for key, entity in self.pinned_entities.items() if entity.ttl > 0
        }

    def commit(self):
        """Remove previous version of existing files from clipboard
        """
        for clipboard_file in self.accessed_files.values():
            clipboard_file.is_new = False
            clipboard_file.is_edited = False
            clipboard_file.previous_file_content = None

    def render_to_markdown(self, shorten: bool = False) -> str:
        """Converts clipboard contents into a structured Markdown string."""
        sections = []

        # Render Todo List
        if self.todo_list:
            todo_section = "### AGENT INTERNAL TODO LIST\n"
            todo_section = "This list is your own to-do list to keep track of your tasks towards achieving your current goals.\n\n"
            for item in self.todo_list:
                status = "[x]" if item.completed else "[ ]"
                todo_section += f"{status} {item.task_desc}\n"
            sections.append(todo_section)

        # Render pinned productivity items
        if self.pinned_entities:
            prod_section = "### USER PRODUCTIVITY SYSTEM (LIVE SYNCED)\n"
            prod_section += "These items are pinned to your clipboard and reflect their real-time state in the database.\n\n"

            # Group by type for cleaner reading
            tasks = [e for e in self.pinned_entities.values() if e.item_type == "task" and e.data]
            projects = [e for e in self.pinned_entities.values() if e.item_type == "project" and e.data]
            journals = [e for e in self.pinned_entities.values() if e.item_type == "journal" and e.data]

            if tasks:
                prod_section += "#### TRACKED TASKS\n"
                for t in tasks:
                    d = t.data
                    prod_section += f"- **[ID: {t.item_id}]** {d.get('title', 'Unknown')} | Status: `{d.get('status', 'Unknown')}`"
                    if d.get("assigned_date"):
                        prod_section += f" | Date: {d.get('assigned_date')}"
                    if d.get("hard_deadline"):
                        prod_section += f" | Deadline: {d.get('hard_deadline')}"
                    prod_section += "\n"

                    if t.resolution == "detail" and not shorten:
                        prod_section += f"  - **Description:** {d.get('description') or 'None'}\n"
                        prod_section += f"  - **Project Links:** {d.get('project_ids', [])}\n"
                prod_section += "\n"

            if projects:
                prod_section += "#### TRACKED PROJECTS\n"
                for p in projects:
                    d = p.data
                    prod_section += f"- **[ID: {p.item_id}]** {d.get('name', 'Unknown')} | Status: `{d.get('status', 'Unknown')}`\n"
                    if p.resolution == "detail" and not shorten:
                        prod_section += f"  - **Description:** {d.get('description') or 'None'}\n"
                        prod_section += f"  - **Deadline:** {d.get('deadline') or 'None'}\n"
                prod_section += "\n"

            if journals:
                prod_section += "#### TRACKED JOURNALS\n"
                for j in journals:
                    d = j.data
                    prod_section += f"- **[ID: {j.item_id}]** {d.get('title') or 'Untitled'} | Type: `{d.get('entry_type', 'Unknown')}` | Ref Date: {d.get('reference_date', 'Unknown')}\n"
                    if j.resolution == "detail" and not shorten:
                        prod_section += f"  - **Content:**\n```markdown\n{d.get('content', '')}\n```\n"
                prod_section += "\n"

            sections.append(prod_section)

        # Render Files
        if self.accessed_files:
            new_files = [file for file in self.accessed_files.values() if file.is_new]
            edited_files = [file for file in self.accessed_files.values() if file.is_edited]
            file_section = "### ACCESSED FILES\n\n"
            file_section += "The following files have been read, written, or edited **by you** so far.\n"
            file_section += "\n\n"

            if new_files:
                file_section += (
                    f"You have read and added **{len(new_files)} files** to the clipboard recently\n"
                )
                file_section += "List of newly added files:\n"
                for new_file in new_files:
                    file_section += f"- `{new_file.file_path}`\n"
                file_section += "\n\n"

            if edited_files:
                file_section += f"You have edited **{len(edited_files)} files** recently:\n"
                file_section += "List of recently edited files:\n"
                for edited_file in edited_files:
                    file_section += f"- `{edited_file.file_path}`\n"
                file_section += "\n\n"

            for _, file in self.accessed_files.items():
                file_section += f"#### File: {file.file_path}\n"
                if file.is_new:
                    file_section += "**Status: Recently Added**\n"
                if file.is_edited:
                    file_section += "**Status: Recently Modified**\n"

                if not shorten:
                    file_section += f"**Current File Content:**\n```\n{file.current_file_content}\n```\n\n"
                    if file.previous_file_content:
                        file_section += (
                            f"**Previous File Content:**\n```\n{file.previous_file_content}\n```\n"
                        )
                else:
                    file_section += (
                        f"**Current File Content:**\n```\n{file.current_file_content[0:50]}...\n```\n"
                    )
                    if file.previous_file_content:
                        file_section += (
                            f"**Previous File Content:**\n```\n{file.previous_file_content[0:50]}...\n```\n"
                        )
                file_section += "\n\n-----\n\n"
            sections.append(file_section)

        # Render tool results
        if self.tool_results:
            tool_section = "### TOOL CALL RESULTS\n\n"
            for _, tool_result in self.tool_results.items():
                tool_section += f"#### Tool Call ID: {tool_result.tool_call_id}\n"
                tool_section += f"Tool: {tool_result.tool_name}\n"
                for res in tool_result.tool_call_results:
                    if not shorten:
                        tool_section += f"```\n{res}\n```\n"
                    else:
                        tool_section += f"```\n{res[:50]}...\n```\n"

                    tool_section += "\n\n-----\n\n"
            sections.append(tool_section)

        # Render memory tag hints
        if self.memory_tag_hints:
            tag_section = "### MEMORY TAGS\n\n"
            tag_section += "Available semantic tags across all memories:\n"
            # Sort alphabetically for stable, predictable output
            for tag in sorted(self.memory_tag_hints):
                count = self.memory_tag_hints[tag]
                tag_section += f"- {tag} ({count})\n"
            sections.append(tag_section)

        if not sections:
            return "Clipboard is currently empty."

        return "\n\n".join(sections)

    def get_accessed_files_paths(self) -> list[Path]:
        """Return a list of paths of all accessed files
        """
        str_paths: list[str] = list(self.accessed_files.keys())
        return [Path(str_path) for str_path in str_paths]


### Schema for workflow events to use with callbacks to communicate events happening during workflow runs
class WorkflowEventType(str, Enum):
    STEP_START = "step_start"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    LOG = "log"
    ERROR = "error"


class WorkflowEvent(BaseModel):
    event_type: WorkflowEventType
    step_id: str | None = None
    message: str
    data: Any | None = None  # Holds the output object or specific metadata


WorkflowCallback = Callable[[WorkflowEvent], Awaitable[None]]


### Schema for workflow manifest yamls
class WorkflowInputType(str, Enum):
    """Data types of workflow inputs for the workflow manifests
    """

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    FILE = "file"
    DIR = "dir"
    LIST_STRING = "list[string]"
    LIST_FILE = "list[file]"


# Map our WorkflowInputType Enum to actual Python types for Pydantic to do run-time validation
TYPE_MAP: dict[WorkflowInputType, Any] = {
    WorkflowInputType.STRING: str,
    WorkflowInputType.INT: int,
    WorkflowInputType.FLOAT: float,
    WorkflowInputType.BOOL: bool,
    WorkflowInputType.FILE: Path,
    WorkflowInputType.DIR: Path,
    WorkflowInputType.LIST_STRING: list[str],
    WorkflowInputType.LIST_FILE: list[Path],
}


class InputDefinition(BaseModel):
    """Defines a variable that the user must provide before the workflow starts."""

    type: WorkflowInputType
    description: str = Field(..., description="Help text for the user")
    default: Any | None = None
    required: bool = False


class StepDefinition(BaseModel):
    """Defines a single executable unit within the workflow."""

    id: str = Field(..., description="Unique ID for this step to reference its data later")
    type: str = Field(..., description="The task type, e.g., 'prompt_agent' or 'file_ingest'")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration passed to the task. Can contain {{ placeholders }}.",
    )
    condition: str | None = Field(
        None, description="A Jinja2 expression. If False, the step is skipped.",
    )


class OutputDefinition(BaseModel):
    """Defines an output from the workflow."""

    description: str = Field(..., description="Help text for the user")
    value: str = Field(
        ..., description="Contain {{ placeholders }} that specifies data source for this output.",
    )


class WorkflowManifest(BaseModel):
    """The root model for a .yaml workflow file."""

    model_config = ConfigDict(extra="forbid")  # Catches typos in top-level YAML keys

    name: str = Field(..., description="Human-readable name of the workflow")
    description: str = Field(..., description="What this workflow actually does")
    version: str = "1.0"

    # Map of input_name -> definition
    inputs: dict[str, InputDefinition] = Field(default_factory=dict)

    # Ordered list of execution steps
    steps: list[StepDefinition]

    # Map of output_name -> definition
    outputs: dict[str, OutputDefinition]

    def validate_runtime_inputs(self, raw_data: dict) -> dict:
        """Validate the raw input data to a workflow against its type definition stored in input dict
        """
        validated = {}
        for name, defn in self.inputs.items():
            raw_val = raw_data.get(name, defn.default)

            # Handle Required / None
            if raw_val is None:
                if defn.required:
                    raise ValueError(f"Input '{name}' is required.")
                validated[name] = None
                continue

            # Type checking the raw value against the required type of the input
            # Handle the edge case where the list has only one element
            list_types = [WorkflowInputType.LIST_STRING, WorkflowInputType.LIST_FILE]
            if defn.type in list_types and isinstance(raw_val, (str, int, float, Path)):
                raw_val = [raw_val]

            target_type = TYPE_MAP.get(defn.type, str)
            try:
                # This automatically handles:
                # - Path conversion
                # - String to Int/Bool
                # - List element validation
                adapter = TypeAdapter(target_type)
                validated[name] = adapter.validate_python(raw_val)

                # Extra check for Files/Dirs
                if defn.type == WorkflowInputType.FILE and not validated[name].is_file():
                    print(f"Warning: {name} path exists but is not a file.")
                if defn.type == WorkflowInputType.DIR and not validated[name].is_dir():
                    print(f"Warning: {name} path exists but is not a directory.")

            except Exception as e:
                raise TypeError(f"Input '{name}' failed validation for type {defn.type}: {e}")

        return validated

    @classmethod
    def from_yaml(cls, path: Path) -> "WorkflowManifest":
        """Utility function to create a WorkflowManifest object directly from reading a YAML file
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


class WorkflowOutput(BaseModel):
    workflow_result: dict[str, Any]
    workspace_directory: Path
