from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


@dataclass
class SandboxFileInfo:
    """Represents a file or directory in the user's sandbox.
    The `relative_path` field serves as the stable identifier for this file.

    Attributes:
        relative_path: The path relative to the sandbox root, used as a stable identifier.
            e.g., "docs/notes.pdf". For the root directory itself, use ".".
        name: The filename or directory name. e.g., "notes.pdf"
        is_dir: True if this is a directory, False if it is a file.
        size: File size in bytes. None for directories.
        mime_type: MIME type guessed from filename. None for directories.
        mtime: Last modified time as Unix timestamp.
        created_at: Creation time as datetime object.
    """

    relative_path: str
    name: str
    is_dir: bool = False
    size: int | None = None
    mime_type: str | None = None
    mtime: float | None = None
    created_at: datetime | None = None


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
    # Whether this agent is the default agent for new sessions
    is_default: bool = False


### Schema for workflow events to use with callbacks to communicate events happening during workflow runs
class WorkflowEventType(StrEnum):
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
class WorkflowInputType(StrEnum):
    """Data types of workflow inputs for the workflow manifests"""

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
        None,
        description="A Jinja2 expression. If False, the step is skipped.",
    )


class OutputDefinition(BaseModel):
    """Defines an output from the workflow."""

    description: str = Field(..., description="Help text for the user")
    value: str = Field(
        ...,
        description="Contain {{ placeholders }} that specifies data source for this output.",
    )
    destination: str | None = Field(
        default=None,
        description=(
            "Relative path in the user's working directory to copy output files to. "
            "For single-file outputs, this is the destination filename. "
            "For multi-file outputs (e.g., a list of file paths), this is treated as a directory "
            "and all files are copied into it. "
            "If omitted, no files are copied out of the job directory."
        ),
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
        """Validate the raw input data to a workflow against its type definition stored in input dict"""
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
                raise TypeError(f"Input '{name}' failed validation for type {defn.type}: {e}") from e

        return validated

    @classmethod
    def from_yaml(cls, path: Path) -> "WorkflowManifest":
        """Utility function to create a WorkflowManifest object directly from reading a YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


class WorkflowOutput(BaseModel):
    workflow_result: dict[str, Any]
    workspace_directory: Path
