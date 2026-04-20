from genesis_core.schemas import LLMModelConfig, LLMProvider
from pydantic import BaseModel


class LLMConfigRead(BaseModel):
    providers: dict[str, LLMProvider]
    models: dict[str, LLMModelConfig]
    default_model: str


class UpdateDefaultModelRequest(BaseModel):
    default_model: str
