from fastapi import APIRouter

from ..dependencies import WorkflowRegDep

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/")
async def list_available_workflows(registry: WorkflowRegDep):
    """Returns a list of all available workflow definitions.
    This helps the frontend dynamically build forms for each workflow.
    """
    manifests = registry.get_all_workflows()
    # We return the model_dump() so FastAPI can serialize the Pydantic models
    return manifests


@router.get("/{workflow_id}")
async def get_workflow_details(workflow_id: str, registry: WorkflowRegDep):
    """Returns the specific manifest for a single workflow.
    """
    manifest = registry.get_workflow(workflow_id)
    if not manifest:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Workflow manifest not found")
    return manifest.model_dump()
