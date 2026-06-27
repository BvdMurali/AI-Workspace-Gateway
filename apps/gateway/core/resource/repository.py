"""
AI Workspace Gateway - Resource Repository
Handles SQLite persistence for resources.
"""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.core.resource.models import Resource
from apps.gateway.core.resource.exceptions import ResourceNotFoundError, ResourceError


class ResourceRepository:
    """Interfaces with the SQLite database to store and retrieve resources."""

    def __init__(self, storage_bootstrap: StorageBootstrap) -> None:
        self.storage = storage_bootstrap

    def _get_connection(self) -> sqlite3.Connection:
        if not self.storage.connection:
            raise ResourceError("Database connection is not open.")
        return self.storage.connection

    def _row_to_resource(self, row: sqlite3.Row) -> Resource:
        """Helper to map a SQLite Row to a Resource object."""
        def parse_dt(val: Any) -> Optional[datetime]:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
            try:
                if " " in val:
                    dt = datetime.strptime(val.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                return None

        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except Exception:
                pass

        tags = []
        if row["tags_json"]:
            try:
                tags = json.loads(row["tags_json"])
            except Exception:
                pass

        return Resource(
            id=row["id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            name=row["name"],
            type=row["type"],
            path=row["path"],
            parent_id=row["parent_id"],
            metadata=metadata,
            tags=tags,
            created_at=parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def create(self, resource: Resource) -> Resource:
        """Persists a new resource in the SQLite database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            
            # Verify workspace exists
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (resource.workspace_id,))
            if not cursor.fetchone():
                from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
                raise WorkspaceNotFoundError(resource.workspace_id)

            # Verify project exists if project_id is provided
            if resource.project_id:
                cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (resource.project_id,))
                if not cursor.fetchone():
                    from apps.gateway.core.project.exceptions import ProjectNotFoundError
                    raise ProjectNotFoundError(resource.project_id)

            cursor.execute(
                """
                INSERT INTO resources (
                    id, workspace_id, project_id, name, type, path, parent_id,
                    metadata_json, tags_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    resource.id,
                    resource.workspace_id,
                    resource.project_id,
                    resource.name,
                    resource.type,
                    resource.path,
                    resource.parent_id,
                    json.dumps(resource.metadata),
                    json.dumps(resource.tags),
                    resource.created_at,
                    resource.updated_at
                )
            )
            conn.commit()
            return resource
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if "Workspace with ID" in str(e) or "Project with ID" in str(e):
                raise
            raise ResourceError(f"Failed to persist resource: {e}") from e

    def get_by_id(self, resource_id: str) -> Optional[Resource]:
        """Retrieves a resource by its unique ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ?;", (resource_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_resource(row)

    def update(self, resource: Resource) -> Resource:
        """Updates an existing resource."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM resources WHERE id = ?;", (resource.id,))
            if not cursor.fetchone():
                raise ResourceNotFoundError(resource.id)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise ResourceError(f"Failed to update resource: {e}") from e

        try:
            cursor.execute("BEGIN TRANSACTION;")
            
            # Verify workspace exists
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (resource.workspace_id,))
            if not cursor.fetchone():
                from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
                raise WorkspaceNotFoundError(resource.workspace_id)

            # Verify project exists if project_id is provided
            if resource.project_id:
                cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (resource.project_id,))
                if not cursor.fetchone():
                    from apps.gateway.core.project.exceptions import ProjectNotFoundError
                    raise ProjectNotFoundError(resource.project_id)

            resource.updated_at = datetime.now(timezone.utc)
            
            cursor.execute(
                """
                UPDATE resources SET
                    workspace_id = ?,
                    project_id = ?,
                    name = ?,
                    type = ?,
                    path = ?,
                    parent_id = ?,
                    metadata_json = ?,
                    tags_json = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    resource.workspace_id,
                    resource.project_id,
                    resource.name,
                    resource.type,
                    resource.path,
                    resource.parent_id,
                    json.dumps(resource.metadata),
                    json.dumps(resource.tags),
                    resource.updated_at,
                    resource.id
                )
            )
            conn.commit()
            return resource
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if "Workspace with ID" in str(e) or "Project with ID" in str(e):
                raise
            raise ResourceError(f"Failed to update resource: {e}") from e

    def delete(self, resource_id: str) -> bool:
        """Deletes a resource. Returns True if deleted, False if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM resources WHERE id = ?;", (resource_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM resources WHERE id = ?;", (resource_id,))
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ResourceError(f"Failed to delete resource: {e}") from e

    def list(
        self,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Resource]:
        """Lists resources with optional filtering and pagination."""
        conn = self._get_connection()
        query = "SELECT * FROM resources"
        conditions = []
        params = []

        if workspace_id:
            conditions.append("workspace_id = ?")
            params.append(workspace_id)
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if type:
            conditions.append("type = ?")
            params.append(type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY name ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [self._row_to_resource(row) for row in cursor.fetchall()]

    def search(
        self,
        query_params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Resource]:
        """
        Searches resources based on query fields, tags, and metadata.
        Supported params:
          - workspace_id: exact match
          - project_id: exact match
          - type: exact match
          - parent_id: exact match
          - name: LIKE match
          - tag: checks if tag exists in tags
          - metadata_key: matches resources having this metadata key
          - metadata_value: matches metadata_key with this value
        """
        conn = self._get_connection()
        query = "SELECT DISTINCT r.* FROM resources r"
        conditions = []
        params = []

        # Filters
        for field in ["workspace_id", "project_id", "type", "parent_id"]:
            if query_params.get(field):
                conditions.append(f"r.{field} = ?")
                params.append(query_params[field])

        if query_params.get("name"):
            conditions.append("r.name LIKE ?")
            params.append(f'%{query_params["name"]}%')

        # Tag filter (JSON array contains query_tag)
        tag_param = query_params.get("tag")
        if tag_param:
            conditions.append("r.tags_json LIKE ?")
            params.append(f'%"{tag_param}"%')

        # Search parameter (name OR tag check)
        search_param = query_params.get("search")
        if search_param:
            conditions.append("(r.name LIKE ? OR r.tags_json LIKE ?)")
            params.extend([f'%{search_param}%', f'%"{search_param}"%'])

        # Metadata key/value filters
        meta_key = query_params.get("metadata_key")
        meta_val = query_params.get("metadata_value")
        if meta_key:
            # Check if metadata_json has key
            conditions.append("json_extract(r.metadata_json, ?) IS NOT NULL")
            params.append(f'$.{meta_key}')
            if meta_val is not None:
                # Check for exact native type match (sqlite3 binds int/bool/str correctly)
                conditions.append("json_extract(r.metadata_json, ?) = ?")
                params.extend([f'$.{meta_key}', meta_val])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY r.name ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [self._row_to_resource(row) for row in cursor.fetchall()]
