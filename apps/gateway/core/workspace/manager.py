"""
AI Workspace Gateway - Workspace Manager
Coordinates workspaces across system boundaries, including Resource registry.
"""

from typing import Any, Dict, List, Optional
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.service import WorkspaceService


class WorkspaceManager:
    """High-level orchestration manager for Workspaces."""

    def __init__(self, service: WorkspaceService, resource_service: Optional[Any] = None) -> None:
        self.service = service
        self.resource_service = resource_service

    async def create_workspace(self, workspace_data: Dict[str, Any]) -> Workspace:
        """Creates a workspace and registers it as a Resource."""
        workspace = await self.service.create_workspace(workspace_data)
        
        # Proactively register the workspace itself in the Resource domain
        import logging
        logging.getLogger("gateway").info(f"WorkspaceManager create_workspace: resource_service is {self.resource_service}")
        if self.resource_service:
            try:
                await self.resource_service.create_resource({
                    "workspace_id": workspace.id,
                    "name": workspace.name,
                    "type": "Workspace",
                    "path": None,
                    "metadata": workspace.config,
                    "tags": []
                })
                conn = self.service.repository._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM resources;")
                rows = cursor.fetchall()
                logging.getLogger("gateway").info(f"DEBUG: resources count in DB is {len(rows)}")
                for r in rows:
                    logging.getLogger("gateway").info(f"DEBUG: resource row in DB: {dict(r)}")
            except Exception as e:
                import logging
                logging.getLogger("gateway").error(f"Error registering workspace resource: {e}", exc_info=True)
                
        return workspace

    async def update_workspace(self, workspace_id: str, updates: Dict[str, Any]) -> Workspace:
        """Updates a workspace and syncs its resource representation."""
        workspace = await self.service.update_workspace(workspace_id, updates)
        
        # Sync name/config with the registered Resource representation
        if self.resource_service:
            try:
                # Find resource of type Workspace representing this workspace
                resources = await self.resource_service.list_resources(
                    workspace_id=workspace_id,
                    type="Workspace"
                )
                for r in resources:
                    if r.name != workspace.name or r.metadata != workspace.config:
                        await self.resource_service.update_resource(r.id, {
                            "name": workspace.name,
                            "metadata": workspace.config
                        })
            except Exception:
                pass
                
        return workspace

    async def delete_workspace(self, workspace_id: str) -> bool:
        """Deletes a workspace."""
        # Note: SQLite ON DELETE CASCADE automatically deletes associated Resources,
        # but we also publish the event inside workspace service.
        return await self.service.delete_workspace(workspace_id)
