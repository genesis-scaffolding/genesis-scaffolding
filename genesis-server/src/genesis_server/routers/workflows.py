from fastapi import APIRouter, HTTPException

from genesis_server.dependencies import CoreDep

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/")
async def list_available_workflows(core: CoreDep):
    """Returns a list of all available workflow definitions."""
    manifests = core.workflow_registry.get_all_workflows()
    return manifests


@router.get("/{workflow_id}")
async def get_workflow_details(workflow_id: str, core: CoreDep):
    """Returns the specific manifest for a single workflow."""
    manifest = core.workflow_registry.get_workflow(workflow_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Workflow manifest not found")
    return manifest.model_dump()
