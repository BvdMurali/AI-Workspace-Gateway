"""
AI Workspace Gateway - V1 Workspace Routers
Exposes REST endpoints for managing, querying, and updating workspaces.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Response, status, Query, Path
from pydantic import BaseModel, Field

from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.manager import WorkspaceManager

router = APIRouter()


class WorkspaceCreateRequest(BaseModel):
    """Schema for creating a new workspace context."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique workspace name.")
    config: Dict[str, Any] = Field(default_factory=dict, description="Extensible configuration key-values.")


class WorkspaceUpdateRequest(BaseModel):
    """Schema for updating an existing workspace context."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Update name.")
    config: Optional[Dict[str, Any]] = Field(None, description="Update configuration key-values.")


def get_manager(request: Request) -> WorkspaceManager:
    """Helper to resolve WorkspaceManager from the DI container."""
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
        
    return container.resolve(WorkspaceManager)


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(request: Request, body: WorkspaceCreateRequest) -> Workspace:
    """Creates a new workspace context."""
    manager = get_manager(request)
    data = body.model_dump(exclude_unset=True)
    return await manager.create_workspace(data)


@router.get("", response_model=List[Workspace])
async def list_workspaces(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
) -> List[Workspace]:
    """Lists workspaces with pagination."""
    manager = get_manager(request)
    return await manager.service.list_workspaces(limit=limit, offset=offset)


@router.get("/{id}", response_model=Workspace)
async def get_workspace(
    request: Request,
    workspace_id: str = Path(..., alias="id", description="Unique workspace ID.")
) -> Workspace:
    """Gets details of a single workspace."""
    manager = get_manager(request)
    return await manager.service.get_workspace(workspace_id)


@router.patch("/{id}", response_model=Workspace)
async def update_workspace(
    request: Request,
    body: WorkspaceUpdateRequest,
    workspace_id: str = Path(..., alias="id", description="Unique workspace ID.")
) -> Workspace:
    """Updates fields of a workspace."""
    manager = get_manager(request)
    updates = body.model_dump(exclude_unset=True)
    return await manager.update_workspace(workspace_id, updates)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    request: Request,
    workspace_id: str = Path(..., alias="id", description="Unique workspace ID.")
) -> Response:
    """Deletes a workspace resource."""
    manager = get_manager(request)
    deleted = await manager.delete_workspace(workspace_id)
    if not deleted:
        from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
        raise WorkspaceNotFoundError(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
