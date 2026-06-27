"""
AI Workspace Gateway - V1 Resource Routers
Exposes REST endpoints for querying resources.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Query

from apps.gateway.core.resource.models import Resource
from apps.gateway.core.resource.manager import ResourceManager

router = APIRouter()


def get_manager(request: Request) -> ResourceManager:
    """Helper to resolve ResourceManager from the DI container."""
    app = request.app
    container = getattr(app.state, "container", None)
    if not container and hasattr(app, "parent") and app.parent:
        container = getattr(app.parent.state, "container", None)
        
    if not container:
        scope_app = request.scope.get("app")
        if scope_app and hasattr(scope_app, "state"):
            container = getattr(scope_app.state, "container", None)
            
    if not container:
        raise RuntimeError("DI Container not found in application state.")
        
    return container.resolve(ResourceManager)


@router.get("", response_model=List[Resource])
async def list_resources(
    request: Request,
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID."),
    project_id: Optional[str] = Query(None, description="Filter by project ID."),
    type: Optional[str] = Query(None, description="Filter by resource type."),
    search: Optional[str] = Query(None, description="Search query across name, tags, or metadata."),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
) -> List[Resource]:
    """Lists or searches resources based on query filters."""
    manager = get_manager(request)
    
    if search or workspace_id or project_id or type:
        # Construct search parameters
        query_params: Dict[str, Any] = {}
        if workspace_id:
            query_params["workspace_id"] = workspace_id
        if project_id:
            query_params["project_id"] = project_id
        if type:
            query_params["type"] = type
            
        if search:
            query_params["search"] = search
            
        return await manager.service.search_resources(query_params, limit=limit, offset=offset)
        
    return await manager.service.list_resources(
        workspace_id=workspace_id,
        project_id=project_id,
        type=type,
        limit=limit,
        offset=offset
    )
