"""
AI Workspace Gateway - Project Service
Implements core business logic for managing projects.
"""

from typing import Any, Dict, List, Optional
import uuid

from apps.gateway.events.bus import EventBus
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.repository import ProjectRepository
from apps.gateway.core.project.validation import ProjectValidation
from apps.gateway.core.project.exceptions import ProjectNotFoundError
from apps.gateway.core.project.events import (
    publish_project_event,
    TOPIC_PROJECT_CREATED,
    TOPIC_PROJECT_UPDATED,
    TOPIC_PROJECT_DELETED
)


class ProjectService:
    """Contains business logic for managing project contexts and lifecycle events."""

    def __init__(self, repository: ProjectRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def create_project(self, project_data: Dict[str, Any]) -> Project:
        """Creates, validates, and persists a new project context."""
        project = Project.model_validate(project_data)
        
        # Validate
        ProjectValidation.validate_create(project)
        
        # Persist
        self.repository.create(project)
        
        # Publish event
        await publish_project_event(self.event_bus, TOPIC_PROJECT_CREATED, project)
        return project

    async def get_project(self, project_id: str) -> Project:
        """Retrieves a project by ID or raises ProjectNotFoundError."""
        project = self.repository.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Project:
        """Updates specific fields of a project."""
        project = await self.get_project(project_id)
        
        # Apply updates
        for field in ["name", "root_path", "repository_metadata", "environment_variables", "tags", "provider_preference"]:
            if field in updates:
                setattr(project, field, updates[field])

        # Validate
        ProjectValidation.validate_create(project)
        
        # Persist
        self.repository.update(project)
        
        # Publish event
        await publish_project_event(self.event_bus, TOPIC_PROJECT_UPDATED, project)
        return project

    async def delete_project(self, project_id: str) -> bool:
        """Deletes project from database and publishes deleted event."""
        project = self.repository.get_by_id(project_id)
        if not project:
            return False
            
        deleted = self.repository.delete(project_id)
        if deleted:
            await publish_project_event(self.event_bus, TOPIC_PROJECT_DELETED, project)
        return deleted

    async def list_projects(self, workspace_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Project]:
        """Lists projects with optional workspace filtering and pagination."""
        return self.repository.list(workspace_id=workspace_id, limit=limit, offset=offset)
