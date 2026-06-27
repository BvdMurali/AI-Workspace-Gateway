"""
AI Workspace Gateway - Workspace Service
Implements core business logic for managing workspaces.
"""

from typing import Any, Dict, List, Optional
import uuid

from apps.gateway.events.bus import EventBus
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.repository import WorkspaceRepository
from apps.gateway.core.workspace.validation import WorkspaceValidation
from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
from apps.gateway.core.workspace.events import (
    publish_workspace_event,
    TOPIC_WORKSPACE_CREATED,
    TOPIC_WORKSPACE_UPDATED,
    TOPIC_WORKSPACE_DELETED
)


class WorkspaceService:
    """Contains business logic for managing workspace contexts and lifecycle events."""

    def __init__(self, repository: WorkspaceRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def create_workspace(self, workspace_data: Dict[str, Any]) -> Workspace:
        """Creates, validates, and persists a new workspace context."""
        workspace = Workspace.model_validate(workspace_data)
        
        # Validate
        WorkspaceValidation.validate_create(workspace)
        
        # Persist
        self.repository.create(workspace)
        
        # Publish event
        await publish_workspace_event(self.event_bus, TOPIC_WORKSPACE_CREATED, workspace)
        return workspace

    async def get_workspace(self, workspace_id: str) -> Workspace:
        """Retrieves a workspace by ID or raises WorkspaceNotFoundError."""
        workspace = self.repository.get_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    async def update_workspace(self, workspace_id: str, updates: Dict[str, Any]) -> Workspace:
        """Updates specific fields of a workspace."""
        workspace = await self.get_workspace(workspace_id)
        
        if "name" in updates:
            workspace.name = updates["name"]
        if "config" in updates:
            # Shallow update or replace
            if isinstance(updates["config"], dict):
                workspace.config = updates["config"]
            else:
                raise ValueError("Config must be a dictionary.")

        # Validate
        WorkspaceValidation.validate_create(workspace)
        
        # Persist
        self.repository.update(workspace)
        
        # Publish event
        await publish_workspace_event(self.event_bus, TOPIC_WORKSPACE_UPDATED, workspace)
        return workspace

    async def delete_workspace(self, workspace_id: str) -> bool:
        """Deletes workspace from database and publishes deleted event."""
        workspace = self.repository.get_by_id(workspace_id)
        if not workspace:
            return False
            
        deleted = self.repository.delete(workspace_id)
        if deleted:
            await publish_workspace_event(self.event_bus, TOPIC_WORKSPACE_DELETED, workspace)
        return deleted

    async def list_workspaces(self, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """Lists workspaces with pagination."""
        return self.repository.list(limit=limit, offset=offset)
