from typing import List

from pydantic import BaseModel, Field


class AgentRead(BaseModel):
    id: str
    name: str
    description: str
    interactive: bool
    read_only: bool
    allowed_tools: List[str]
    allowed_agents: List[str]
    system_prompt: str
    # We include the model name but NOT the provider's API key
    model_name: str | None = None


class AgentCreate(BaseModel):
    name: str = Field(..., description="The display name of the agent")
    description: str = Field(..., description="A short description of what the agent does")
    system_prompt: str = Field(..., description="The system instructions (body of the markdown file)")
    interactive: bool = True
    allowed_tools: List[str] = []
    allowed_agents: List[str] = []
    model_name: str | None = None


class AgentEdit(BaseModel):
    description: str = Field(..., description="A short description of what the agent does")
    system_prompt: str = Field(..., description="The system instructions (body of the markdown file)")
    interactive: bool = True
    allowed_tools: List[str] = []
    allowed_agents: List[str] = []
    model_name: str | None = None
