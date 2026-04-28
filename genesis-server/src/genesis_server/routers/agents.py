from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from genesis_core.configs import Config

from genesis_server.dependencies import CoreDep, get_server_settings
from genesis_server.schemas.agent import AgentCreate, AgentEdit, AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentRead])
async def list_agents(core: CoreDep):
    """Returns a list of all available agents blueprints."""
    results = []
    for id, blueprint in core.agent_registry.blueprints.items():
        results.append(
            AgentRead(
                id=id,
                name=blueprint.name,
                description=blueprint.description,
                interactive=blueprint.interactive,
                read_only=blueprint.read_only,
                allowed_tools=blueprint.allowed_tools,
                allowed_agents=blueprint.allowed_agents,
                system_prompt=blueprint.system_prompt,
                model_name=blueprint.model_name,
                is_default=blueprint.is_default,
            ),
        )
    return results


@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    core: CoreDep,
    settings: Annotated[Config, Depends(get_server_settings)],
):
    """Creates a new custom agent by saving a markdown file to the user's directory."""
    agent_dict = payload.model_dump()
    llm_model_name = payload.model_name

    # If user does not provide model name, use the default model of that user
    if not llm_model_name:
        default_llm_model_name = settings.default_model
        agent_dict["model_name"] = default_llm_model_name
        llm_model_name = default_llm_model_name

    # If user does provide a model name, verify that it exists and its the provider exist
    llm_config = settings.models.get(llm_model_name, None)
    if not llm_config:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find the requested llm model: {llm_model_name}",
        )

    provider_name = llm_config.provider
    provider_config = settings.providers.get(provider_name, None)
    if not provider_config:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find the requested provider {provider_name} of the llm model {llm_model_name}",
        )

    try:
        # Save to disk
        agent_id = core.agent_registry.add_agent(agent_dict)

        # Retrieve the newly created blueprint to return it
        blueprint = core.agent_registry.blueprints.get(agent_id)
        if not blueprint:
            raise HTTPException(status_code=500, detail="Failed to reload agent after saving.")

        return AgentRead(
            id=agent_id,
            name=blueprint.name,
            description=blueprint.description,
            interactive=blueprint.interactive,
            read_only=blueprint.read_only,
            allowed_tools=blueprint.allowed_tools,
            allowed_agents=blueprint.allowed_agents,
            system_prompt=blueprint.system_prompt,
            model_name=blueprint.model_name,
            is_default=blueprint.is_default,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create agent: {e!s}") from e


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent_details(
    agent_id: str,
    core: CoreDep,
):
    """Returns the full metadata for a specific agent."""
    blueprint = core.agent_registry.blueprints.get(agent_id)
    if not blueprint:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found in registry.")

    return AgentRead(
        id=agent_id,
        name=blueprint.name,
        description=blueprint.description,
        interactive=blueprint.interactive,
        read_only=blueprint.read_only,
        allowed_tools=blueprint.allowed_tools,
        allowed_agents=blueprint.allowed_agents,
        system_prompt=blueprint.system_prompt,
        model_name=blueprint.model_name,
        is_default=blueprint.is_default,
    )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Agent not found"},
        403: {"description": "Agent is read‑only"},
        500: {"description": "Internal server error while deleting"},
    },
)
async def delete_agent(
    agent_id: str,
    core: CoreDep,
):
    """Delete an agent from the registry."""
    try:
        core.agent_registry.delete_agent(agent_id)

    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        if "read-only" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent.",
        ) from exc


@router.patch(
    "/{agent_id}",
    response_model=AgentRead,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Agent not found"},
        403: {"description": "Agent is read‑only"},
        500: {"description": "Failed to persist changes"},
    },
)
async def update_agent(
    agent_id: str,
    payload: AgentEdit,
    core: CoreDep,
):
    """Update an existing agent definition."""
    try:
        core.agent_registry.edit_agent(agent_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        ) from exc
    except ValueError as exc:
        if "read-only" in str(exc) or "read_only" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit agent.",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist the updated agent file.",
        ) from exc

    blueprint = core.agent_registry.blueprints.get(agent_id)
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload the updated agent from the registry.",
        )

    return AgentRead(
        id=agent_id,
        name=blueprint.name,
        description=blueprint.description,
        interactive=blueprint.interactive,
        read_only=blueprint.read_only,
        allowed_tools=blueprint.allowed_tools,
        allowed_agents=blueprint.allowed_agents,
        system_prompt=blueprint.system_prompt,
        model_name=blueprint.model_name,
        is_default=blueprint.is_default,
    )
