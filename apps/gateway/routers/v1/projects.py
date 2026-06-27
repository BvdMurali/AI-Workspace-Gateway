"""
AI Workspace Gateway - V1 Project Routers
Exposes REST endpoints for managing and querying projects.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, status, Query
from pydantic import BaseModel, Field

from apps.gateway.core.project.models import Project
from apps.gateway.core.project.manager import ProjectManager

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    """Schema for creating a new project context."""
    workspace_id: str = Field(..., description="Target workspace ID.")
    name: str = Field(..., min_length=1, max_length=255, description="Unique project name.")
    root_path: str = Field(..., min_length=1, description="Absolute local directory path.")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables.")
    tags: List[str] = Field(default_factory=list, description="Tags associated with project.")
    provider_preference: Optional[str] = Field(None, description="Optional provider preference.")


def get_manager(request: Request) -> ProjectManager:
    """Helper to resolve ProjectManager from the DI container."""
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
        
    return container.resolve(ProjectManager)


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(request: Request, body: ProjectCreateRequest) -> Project:
    """Creates a new project context and discovers repository metadata."""
    manager = get_manager(request)
    data = body.model_dump(exclude_unset=True)
    return await manager.create_project(data)


@router.get("", response_model=List[Project])
async def list_projects(
    request: Request,
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID."),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
) -> List[Project]:
    """Lists projects with optional filtering."""
    manager = get_manager(request)
    return await manager.service.list_projects(workspace_id=workspace_id, limit=limit, offset=offset)
