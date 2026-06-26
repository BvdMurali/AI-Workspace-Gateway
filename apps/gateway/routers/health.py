"""
AI Workspace Gateway - Health Routers
Exposes REST endpoints for system health, readiness, and software version.
"""

from fastapi import APIRouter, Request, Response, status
from apps.gateway.health.service import HealthService

router = APIRouter()


@router.get("/health")
async def get_health(request: Request, response: Response) -> dict:
    """Returns the comprehensive health stats of the Gateway."""
    container = request.app.state.container
    health_service = container.resolve(HealthService)
    
    health_status = await health_service.check_health()
    if health_status["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
    return health_status


@router.get("/ready")
async def get_ready(request: Request, response: Response) -> dict:
    """Returns readiness status. If booting or shutting down, returns 503."""
    # Check if application lifecycle state is ready
    lifecycle = getattr(request.app.state, "lifecycle", None)
    if lifecycle and lifecycle.is_ready():
        return {"status": "ready"}
        
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready"}


@router.get("/version")
async def get_version(request: Request) -> dict:
    """Returns the current software version of the Gateway."""
    container = request.app.state.container
    health_service = container.resolve(HealthService)
    return {"version": health_service.get_version()}
