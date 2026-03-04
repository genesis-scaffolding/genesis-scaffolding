from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from myproject_core import agent
from myproject_core.agent_registry import AgentRegistry

from ..dependencies import get_agent_registry
from ..schemas.agent import AgentCreate, AgentRead

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
                allowed_tools=blueprint.allowed_tools,
                allowed_agents=blueprint.allowed_agents,
                model_name=blueprint.llm_config.model if blueprint.llm_config else None,
            )
        )
    return results


@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, agent_reg: AgentRegistry = Depends(get_agent_registry)):
    """
    Creates a new custom agent by saving a markdown file to the user's directory.
    """
    # Prepare data for the registry
    agent_dict = payload.model_dump()

    # Handle LLM configuration mapping
    # If the user provided a model_name, we structure it for AgentConfig
    if payload.model_name:
        agent_dict["llm_config"] = {
            "model": payload.model_name,
            # Provider info will be filled by registry defaults if missing
        }

    # TEMPORARILY REMOVE THE LLM CONFIG FROM AGENT CONFIG
    # WILL ADD BACK WHEN WE SUPPORT USER-DEFINED LLM PROVIDER
    if "llm_config" in agent_dict.keys():
        del agent_dict["llm_config"]

    try:
        # Save to disk
        agent_id = agent_reg.save_agent(agent_dict)

        # Retrieve the newly created blueprint to return it
        blueprint = agent_reg.blueprints.get(agent_id)
        if not blueprint:
            raise HTTPException(status_code=500, detail="Failed to reload agent after saving.")

        return AgentRead(
            id=agent_id,
            name=blueprint.name,
            description=blueprint.description,
            interactive=blueprint.interactive,
            allowed_tools=blueprint.allowed_tools,
            allowed_agents=blueprint.allowed_agents,
            model_name=blueprint.llm_config.model if blueprint.llm_config else None,
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
        allowed_tools=blueprint.allowed_tools,
        allowed_agents=blueprint.allowed_agents,
        model_name=blueprint.llm_config.model if blueprint.llm_config else None,
    )
