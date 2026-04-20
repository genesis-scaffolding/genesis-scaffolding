from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from genesis_core.configs import Config
from genesis_core.schemas import LLMModelConfig, LLMProvider

from ..dependencies import get_current_active_user, get_user_config, get_user_workdir
from ..models.user import User
from ..schemas.llm_config import LLMConfigRead, UpdateDefaultModelRequest
from ..utils.config_persistence import update_user_top_level_config, update_user_yaml_config

router = APIRouter(prefix="/configs/llm", tags=["llm-config"])


@router.get("/", response_model=LLMConfigRead)
async def get_llm_config(config: Annotated[Config, Depends(get_user_config)]):
    """Retrieve current LLM providers and models (merged system + user)"""
    return {"providers": config.providers, "models": config.models, "default_model": config.default_model}


@router.post("/providers/{nickname}", status_code=status.HTTP_201_CREATED)
async def save_provider(
    nickname: str,
    provider_data: LLMProvider,
    user: Annotated[User, Depends(get_current_active_user)],
    user_dir: Annotated[Path, Depends(get_user_workdir)],
):
    """Create or update an LLM provider in user's configs.yaml"""
    update_user_yaml_config(user_dir, "providers", nickname, provider_data.model_dump(exclude_none=True))
    return {"message": f"Provider '{nickname}' saved successfully"}


@router.delete("/providers/{nickname}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    nickname: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_dir: Annotated[Path, Depends(get_user_workdir)],
    config: Annotated[Config, Depends(get_user_config)],
):
    """Remove a provider from user's configs.yaml"""
    # Validation: Don't delete if models are using it
    dependent_models = [m for m, cfg in config.models.items() if cfg.provider == nickname]
    if dependent_models:
        raise HTTPException(
            status_code=400, detail=f"Cannot delete provider. It is used by models: {dependent_models}",
        )

    update_user_yaml_config(user_dir, "providers", nickname, None)


@router.post("/models/{nickname}", status_code=status.HTTP_201_CREATED)
async def save_model(
    nickname: str,
    model_data: LLMModelConfig,
    user: Annotated[User, Depends(get_current_active_user)],
    user_dir: Annotated[Path, Depends(get_user_workdir)],
    config: Annotated[Config, Depends(get_user_config)],
):
    """Create or update an LLM model in user's configs.yaml"""
    # Validation: Ensure the provider exists
    if model_data.provider not in config.providers:
        raise HTTPException(status_code=400, detail=f"Provider '{model_data.provider}' not found")

    update_user_yaml_config(user_dir, "models", nickname, model_data.model_dump(exclude_none=True))
    return {"message": f"Model '{nickname}' saved successfully"}


@router.delete("/models/{nickname}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    nickname: str,
    user: Annotated[User, Depends(get_current_active_user)],
    user_dir: Annotated[Path, Depends(get_user_workdir)],
    config: Annotated[Config, Depends(get_user_config)],
):
    """Remove a model from user's configs.yaml"""
    if config.default_model == nickname:
        raise HTTPException(status_code=400, detail="Cannot delete the default model")

    update_user_yaml_config(user_dir, "models", nickname, None)


@router.patch("/settings")
async def update_settings(
    payload: UpdateDefaultModelRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    user_dir: Annotated[Path, Depends(get_user_workdir)],
    config: Annotated[Config, Depends(get_user_config)],
):
    """Update general settings like default_model"""
    if payload.default_model not in config.models:
        raise HTTPException(status_code=400, detail=f"Model '{payload.default_model}' does not exist")

    update_user_top_level_config(user_dir, {"default_model": payload.default_model})
    return {"message": "Settings updated"}
