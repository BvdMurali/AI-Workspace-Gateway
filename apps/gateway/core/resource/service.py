"""
AI Workspace Gateway - Resource Service
Implements core business logic for managing resources.
"""

from typing import Any, Dict, List, Optional
import uuid

from apps.gateway.events.bus import EventBus
from apps.gateway.core.resource.models import Resource
from apps.gateway.core.resource.repository import ResourceRepository
from apps.gateway.core.resource.validation import ResourceValidation
from apps.gateway.core.resource.exceptions import ResourceNotFoundError
from apps.gateway.core.resource.events import (
    publish_resource_event,
    TOPIC_RESOURCE_CREATED,
    TOPIC_RESOURCE_UPDATED,
    TOPIC_RESOURCE_DELETED
)


class ResourceService:
    """Contains business logic for managing resource contexts and lifecycle events."""

    def __init__(self, repository: ResourceRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def create_resource(self, resource_data: Dict[str, Any]) -> Resource:
        """Creates, validates, and persists a new resource context."""
        resource = Resource.model_validate(resource_data)
        
        # Validate
        ResourceValidation.validate_create(resource)
        
        # Persist
        self.repository.create(resource)
        
        # Publish event
        await publish_resource_event(self.event_bus, TOPIC_RESOURCE_CREATED, resource)
        return resource

    async def get_resource(self, resource_id: str) -> Resource:
        """Retrieves a resource by ID or raises ResourceNotFoundError."""
        resource = self.repository.get_by_id(resource_id)
        if not resource:
            raise ResourceNotFoundError(resource_id)
        return resource

    async def update_resource(self, resource_id: str, updates: Dict[str, Any]) -> Resource:
        """Updates specific fields of a resource."""
        resource = await self.get_resource(resource_id)
        
        # Apply updates
        for field in ["workspace_id", "project_id", "name", "type", "path", "parent_id", "metadata", "tags"]:
            if field in updates:
                setattr(resource, field, updates[field])

        # Validate
        ResourceValidation.validate_create(resource)
        
        # Persist
        self.repository.update(resource)
        
        # Publish event
        await publish_resource_event(self.event_bus, TOPIC_RESOURCE_UPDATED, resource)
        return resource

    async def delete_resource(self, resource_id: str) -> bool:
        """Deletes resource from database and publishes deleted event."""
        resource = self.repository.get_by_id(resource_id)
        if not resource:
            return False
            
        deleted = self.repository.delete(resource_id)
        if deleted:
            await publish_resource_event(self.event_bus, TOPIC_RESOURCE_DELETED, resource)
        return deleted

    async def list_resources(
        self,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Resource]:
        """Lists resources with optional filtering and pagination."""
        return self.repository.list(workspace_id=workspace_id, project_id=project_id, type=type, limit=limit, offset=offset)

    async def search_resources(
        self,
        query_params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Resource]:
        """Searches resources based on query fields, tags, and metadata."""
        return self.repository.search(query_params=query_params, limit=limit, offset=offset)
