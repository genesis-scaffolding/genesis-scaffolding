from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from myproject_core.agent_registry import AgentRegistry
from myproject_core.configs import Config

from ..dependencies import get_agent_registry, get_user_config
from ..schemas.agent import AgentCreate, AgentEdit, AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[AgentRead])
async def list_agents(agent_reg: AgentRegistry = Depends(get_agent_registry)):
    """
    Returns a list of all available agents blueprints.
    """
    results = []
    for id, blueprint in agent_reg.blueprints.items():
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
            )
        )
    return results


@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    agent_reg: Annotated[AgentRegistry, Depends(get_agent_registry)],
    user_settings: Annotated[Config, Depends(get_user_config)],
):
    """
    Creates a new custom agent by saving a markdown file to the user's directory.
    """
    # Prepare data for the registry
    agent_dict = payload.model_dump()
    llm_model_name = payload.model_name

    # If user does not provide model name, use the default model of that user
    if not llm_model_name:
        default_llm_model_name = user_settings.default_model
        agent_dict["model_name"] = default_llm_model_name
        llm_model_name = default_llm_model_name

    # If user does provide a model name, verify that it exists and its the provider exist
    llm_config = user_settings.models.get(llm_model_name, None)
    if not llm_config:
        raise HTTPException(
            status_code=400, detail=f"Cannot find the requested llm model: {llm_model_name}"
        )

    provider_name = llm_config.provider
    provider_config = user_settings.providers.get(provider_name, None)
    if not provider_config:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find the requested provider {provider_name} of the llm model {llm_model_name}",
        )

    try:
        # Save to disk
        agent_id = agent_reg.add_agent(agent_dict)

        # Retrieve the newly created blueprint to return it
        blueprint = agent_reg.blueprints.get(agent_id)
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
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create agent: {str(e)}")


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent_details(agent_id: str, agent_reg: AgentRegistry = Depends(get_agent_registry)):
    """
    Returns the full metadata for a specific agent.
    """
    blueprint = agent_reg.blueprints.get(agent_id)
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
    agent_reg: "AgentRegistry" = Depends(get_agent_registry),  # type: ignore[name-defined]
):
    """
    Delete an agent from the registry.

    - If the agent does not exist, a 404 is returned.
    - If the agent exists but is marked ``read_only``, a 403 is returned.
    - On successful deletion a 204 No Content is sent.
    """
    try:
        # The underlying registry method does the actual file removal.
        agent_reg.delete_agent(agent_id)

    except ValueError as exc:
        # The delete_agent implementation raises ValueError with a specific message.
        if "not found" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            )
        if "read-only" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            )
        # Any other ValueError is unexpected – treat it as a server error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent.",
        )

    # Returning ``None`` with the 204 status code tells FastAPI to send an empty body.
    return None


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
    agent_reg: Annotated[AgentRegistry, Depends(get_agent_registry)],
):
    """
    Update an existing agent definition.

    * The file is looked up in the **last** directory of ``settings.path.agent_search_paths``.
    * ``system_prompt`` becomes the markdown **body**; all other fields are treated as metadata.
    * If the agent does not exist → 404.
    * If the agent is marked ``read_only`` → 403.
    * On success the updated agent data is returned as ``AgentRead``.
    """
    try:
        agent_reg.edit_agent(agent_id, payload.model_dump())
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )
    except ValueError as exc:
        if "read-only" in str(exc) or "read_only" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            )
        # Anything else is unexpected – treat as a server error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit agent.",
        )
    except OSError as exc:
        # Writing the file failed for some OS‑level reason.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist the updated agent file.",
        ) from exc

    blueprint = agent_reg.blueprints.get(agent_id)
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
    )
