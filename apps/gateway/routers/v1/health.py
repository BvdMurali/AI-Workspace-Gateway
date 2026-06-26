"""
AI Workspace Gateway - V1 Health Routers
Exposes REST endpoints for system health, readiness, and software version under v1.
"""

from fastapi import APIRouter, Request, Response, status
from apps.gateway.health.service import HealthService

router = APIRouter()


@router.get("/health")
async def get_health(request: Request, response: Response) -> dict:
    """Returns the comprehensive health stats of the Gateway."""
    # Retrieve the container from the current app (handles both main app or mounted sub-app state)
    app = request.app
    # If request is routed via mounted sub-app, container is in the parent app state
    container = getattr(app.state, "container", None)
    if not container and hasattr(app, "parent") and app.parent:
        container = getattr(app.parent.state, "container", None)
    
    if not container:
        # Fallback to fetching container from root app state if state is not directly on sub-app
        parent_app = getattr(request.scope.get("app"), "parent", None)
        if parent_app:
            container = getattr(parent_app.state, "container", None)
            
    if not container:
        # Try finding container on request.scope["app"].state (FastAPI standard)
        scope_app = request.scope.get("app")
        if scope_app and hasattr(scope_app, "state"):
            container = getattr(scope_app.state, "container", None)

    if not container:
        # Final fallback
        raise RuntimeError("DI Container not found in application state.")
        
    health_service = container.resolve(HealthService)
    health_status = await health_service.check_health()
    
    if health_status["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
    return health_status


@router.get("/ready")
async def get_ready(request: Request, response: Response) -> dict:
    """Returns readiness status. If booting or shutting down, returns 503."""
    # Check if application lifecycle state is ready
    app = request.app
    lifecycle = getattr(app.state, "lifecycle", None)
    
    if not lifecycle:
        # Try finding on parent if mounted
        scope_app = request.scope.get("app")
        if scope_app and hasattr(scope_app, "state"):
            lifecycle = getattr(scope_app.state, "lifecycle", None)

    if lifecycle and lifecycle.is_ready():
        return {"status": "ready"}
        
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready"}


@router.get("/version")
async def get_version(request: Request) -> dict:
    """Returns the current software version of the Gateway."""
    app = request.app
    container = getattr(app.state, "container", None)
    if not container:
        scope_app = request.scope.get("app")
        if scope_app and hasattr(scope_app, "state"):
            container = getattr(scope_app.state, "container", None)
            
    if not container:
        raise RuntimeError("DI Container not found in application state.")
        
    health_service = container.resolve(HealthService)
    return {"version": health_service.get_version()}
