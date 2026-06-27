"""
AI Workspace Gateway - V1 Session Routers
Exposes REST endpoints for querying active developer sessions.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Query

from apps.gateway.core.session.models import Session, SessionState
from apps.gateway.core.session.manager import SessionManager

router = APIRouter()


def get_manager(request: Request) -> SessionManager:
    """Helper to resolve SessionManager from the DI container."""
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
        
    return container.resolve(SessionManager)


@router.get("", response_model=List[Session])
async def list_sessions(
    request: Request,
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID."),
    project_id: Optional[str] = Query(None, description="Filter by project ID."),
    state: Optional[SessionState] = Query(None, description="Filter by session state."),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
) -> List[Session]:
    """Lists sessions with pagination and filters."""
    manager = get_manager(request)
    return await manager.service.list_sessions(
        workspace_id=workspace_id,
        project_id=project_id,
        state=state,
        limit=limit,
        offset=offset
    )
