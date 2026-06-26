"""
AI Workspace Gateway - V1 Execution Routers
Exposes REST endpoints for managing, querying, and updating executions.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Request, Response, status, Query, Path

from apps.gateway.core.execution.models import Execution, ExecutionState, RetryPolicy
from apps.gateway.core.execution.manager import ExecutionManager
from apps.gateway.core.execution.exceptions import ExecutionValidationError
from pydantic import BaseModel, Field

router = APIRouter()


class ExecutionCreateRequest(BaseModel):
    """Schema for creating a new execution context."""
    correlation_id: Optional[str] = Field(default=None, description="Optional correlation ID for distributed tracing.")
    workspace_id: Optional[str] = Field(default=None, description="Optional workspace association ID.")
    provider_id: Optional[str] = Field(default=None, description="Optional provider identifier.")
    tool_id: Optional[str] = Field(default=None, description="Optional tool identifier.")
    priority: int = Field(default=0, description="Priority level of execution (higher is higher priority).")
    timeout: float = Field(default=300.0, gt=0.0, description="Execution timeout in seconds.")
    retry_policy: Optional[RetryPolicy] = Field(default_factory=RetryPolicy, description="Retry policy configuration.")
    owner: Optional[str] = Field(default=None, description="Owner username or email.")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables dict.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata schema.")
    tags: List[str] = Field(default_factory=list, description="Categorization tags.")


class ExecutionUpdateRequest(BaseModel):
    """Schema for updating an existing execution context (supports partial updates)."""
    state: Optional[ExecutionState] = Field(default=None, description="Execution state transition target.")
    priority: Optional[int] = Field(default=None, description="Update priority level.")
    timeout: Optional[float] = Field(default=None, gt=0.0, description="Update execution timeout in seconds.")
    owner: Optional[str] = Field(default=None, description="Update owner identifier.")
    environment_variables: Optional[Dict[str, str]] = Field(default=None, description="Update environment variables.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Update metadata fields.")
    tags: Optional[List[str]] = Field(default=None, description="Update tags list.")
    scheduled_at: Optional[datetime] = Field(default=None, description="Update scheduled execution timestamp.")


def get_manager(request: Request) -> ExecutionManager:
    """Helper to resolve ExecutionManager from the DI container."""
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
        
    return container.resolve(ExecutionManager)


@router.post("", response_model=Execution, status_code=status.HTTP_201_CREATED)
async def create_execution(request: Request, body: ExecutionCreateRequest) -> Execution:
    """Creates a new execution context."""
    manager = get_manager(request)
    # Convert body to dictionary and remove None values to let model defaults apply
    data = body.model_dump(exclude_unset=True)
    return await manager.create_execution(data)


@router.get("", response_model=List[Execution])
async def list_executions(
    request: Request,
    state: Optional[ExecutionState] = Query(None, description="Filter by state."),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace."),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    search: Optional[str] = Query(None, description="Search query across tags, correlation ID, etc.")
) -> List[Execution]:
    """Lists or searches executions based on query filters."""
    manager = get_manager(request)
    
    if search:
        # Construct search query parameters
        query_params: Dict[str, Any] = {}
        if state:
            query_params["state"] = state
        if workspace_id:
            query_params["workspace_id"] = workspace_id
            
        # If search matches a UUID format, set correlation_id; otherwise search by tag
        if len(search) == 36:
            query_params["correlation_id"] = search
        else:
            query_params["tag"] = search
            
        return await manager.service.search_executions(query_params, limit=limit, offset=offset)
        
    return await manager.service.list_executions(state=state, workspace_id=workspace_id, limit=limit, offset=offset)


@router.get("/{id}", response_model=Execution)
async def get_execution(
    request: Request,
    execution_id: str = Path(..., alias="id", description="Unique execution ID.")
) -> Execution:
    """Gets details of a single execution."""
    manager = get_manager(request)
    return await manager.service.get_execution(execution_id)


@router.patch("/{id}", response_model=Execution)
async def update_execution(
    request: Request,
    body: ExecutionUpdateRequest,
    execution_id: str = Path(..., alias="id", description="Unique execution ID.")
) -> Execution:
    """Updates fields or triggers a state transition for an execution."""
    manager = get_manager(request)
    
    updates = body.model_dump(exclude_unset=True)
    
    # 1. Trigger state transition if specified
    if "state" in updates:
        target_state = updates.pop("state")
        await manager.service.transition_state(execution_id, target_state)
        
    # 2. If there are other updates, perform update_execution
    if updates:
        await manager.service.update_execution(execution_id, updates)
        
    return await manager.service.get_execution(execution_id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    request: Request,
    execution_id: str = Path(..., alias="id", description="Unique execution ID.")
) -> Response:
    """Deletes an execution resource from storage."""
    manager = get_manager(request)
    deleted = await manager.service.delete_execution(execution_id)
    if not deleted:
        from apps.gateway.core.execution.exceptions import ExecutionNotFoundError
        raise ExecutionNotFoundError(execution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
