"""
AI Workspace Gateway - Project Manager
Coordinates projects across system boundaries, repository discovery, and Resource registry.
"""

from typing import Any, Dict, List, Optional
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.service import ProjectService
from apps.gateway.core.project.discovery import RepositoryDiscoveryService


class ProjectManager:
    """High-level orchestration manager for Projects."""

    def __init__(
        self,
        service: ProjectService,
        discovery_service: RepositoryDiscoveryService,
        resource_service: Optional[Any] = None
    ) -> None:
        self.service = service
        self.discovery_service = discovery_service
        self.resource_service = resource_service

    async def create_project(self, project_data: Dict[str, Any]) -> Project:
        """Creates a project, runs git repository discovery, and registers resources."""
        # 1. Discover local Git repository at project's root path if not already provided
        root_path = project_data.get("root_path")
        if root_path and not project_data.get("repository_metadata"):
            try:
                # Run discovery at max_depth=1 (exact path or immediate child) to keep it fast
                discovered = await self.discovery_service.discover_repositories_async(root_path, max_depth=1)
                if discovered:
                    project_data["repository_metadata"] = discovered[0]
            except Exception:
                pass  # Do not block project creation due to discovery failure

        # 2. Create the project via the service
        project = await self.service.create_project(project_data)

        # 3. Proactively register Project and Git Repository in Resource domain
        if self.resource_service:
            try:
                # Register Project Resource
                await self.resource_service.create_resource({
                    "workspace_id": project.workspace_id,
                    "project_id": project.id,
                    "name": project.name,
                    "type": "Project",
                    "path": project.root_path,
                    "metadata": {
                        "provider_preference": project.provider_preference,
                        "tags": project.tags
                    },
                    "tags": project.tags
                })

                # If git repository is detected, register it as a resource too
                repo_meta = project.repository_metadata
                if repo_meta:
                    await self.resource_service.create_resource({
                        "workspace_id": project.workspace_id,
                        "project_id": project.id,
                        "name": repo_meta.get("name", f"{project.name} Repository"),
                        "type": "Git Repository",
                        "path": repo_meta.get("root_path", project.root_path),
                        "metadata": repo_meta,
                        "tags": ["git", "repository"]
                    })
            except Exception as e:
                import logging
                logging.getLogger("gateway").error(f"Error registering project resources: {e}", exc_info=True)

        return project

    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Project:
        """Updates a project and syncs its resource representation."""
        project = await self.service.update_project(project_id, updates)

        # Sync representation in resource catalog
        if self.resource_service:
            try:
                # Find Project resource representing this project
                resources = await self.resource_service.list_resources(
                    project_id=project_id,
                    type="Project"
                )
                for r in resources:
                    await self.resource_service.update_resource(r.id, {
                        "name": project.name,
                        "path": project.root_path,
                        "metadata": {
                            "provider_preference": project.provider_preference,
                            "tags": project.tags
                        },
                        "tags": project.tags
                    })
            except Exception:
                pass

        return project

    async def delete_project(self, project_id: str) -> bool:
        """Deletes a project."""
        # SQLite ON DELETE CASCADE handles deleting related resources and sessions
        return await self.service.delete_project(project_id)
