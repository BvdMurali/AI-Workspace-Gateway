"""
AI Workspace Gateway - Resource Manager
Coordinates resource catalog updates and queries.
"""

from typing import Any, Dict, List, Optional
from apps.gateway.core.resource.models import Resource
from apps.gateway.core.resource.service import ResourceService


class ResourceManager:
    """High-level orchestration manager for Resources."""

    def __init__(self, service: ResourceService) -> None:
        self.service = service

    async def create_resource(self, resource_data: Dict[str, Any]) -> Resource:
        """Creates a new resource context."""
        return await self.service.create_resource(resource_data)

    async def update_resource(self, resource_id: str, updates: Dict[str, Any]) -> Resource:
        """Updates an existing resource context."""
        return await self.service.update_resource(resource_id, updates)

    async def delete_resource(self, resource_id: str) -> bool:
        """Deletes a resource."""
        return await self.service.delete_resource(resource_id)
