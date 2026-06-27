"""
AI Workspace Gateway - Project Repository
Handles SQLite persistence for projects.
"""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.core.project.models import Project
from apps.gateway.core.project.exceptions import ProjectNotFoundError, ProjectError


class ProjectRepository:
    """Interfaces with the SQLite database to store and retrieve projects."""

    def __init__(self, storage_bootstrap: StorageBootstrap) -> None:
        self.storage = storage_bootstrap

    def _get_connection(self) -> sqlite3.Connection:
        if not self.storage.connection:
            raise ProjectError("Database connection is not open.")
        return self.storage.connection

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        """Helper to map a SQLite Row to a Project object."""
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

        # JSON decodes
        repo_metadata = {}
        if row["repository_metadata_json"]:
            try:
                repo_metadata = json.loads(row["repository_metadata_json"])
            except Exception:
                pass

        env_vars = {}
        if row["environment_variables_json"]:
            try:
                env_vars = json.loads(row["environment_variables_json"])
            except Exception:
                pass

        tags = []
        if row["tags_json"]:
            try:
                tags = json.loads(row["tags_json"])
            except Exception:
                pass

        return Project(
            id=row["id"],
            workspace_id=row["workspace_id"],
            name=row["name"],
            root_path=row["root_path"],
            repository_metadata=repo_metadata,
            environment_variables=env_vars,
            tags=tags,
            provider_preference=row["provider_preference"],
            created_at=parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def create(self, project: Project) -> Project:
        """Persists a new project in the SQLite database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            
            # Verify workspace exists
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (project.workspace_id,))
            if not cursor.fetchone():
                from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
                raise WorkspaceNotFoundError(project.workspace_id)

            cursor.execute(
                """
                INSERT INTO projects (
                    id, workspace_id, name, root_path, repository_metadata_json,
                    environment_variables_json, tags_json, provider_preference, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project.id,
                    project.workspace_id,
                    project.name,
                    project.root_path,
                    json.dumps(project.repository_metadata),
                    json.dumps(project.environment_variables),
                    json.dumps(project.tags),
                    project.provider_preference,
                    project.created_at,
                    project.updated_at
                )
            )
            conn.commit()
            return project
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if "Workspace with ID" in str(e):
                raise
            raise ProjectError(f"Failed to persist project: {e}") from e

    def get_by_id(self, project_id: str) -> Optional[Project]:
        """Retrieves a project by its unique ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_project(row)

    def update(self, project: Project) -> Project:
        """Updates an existing project."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (project.id,))
            if not cursor.fetchone():
                raise ProjectNotFoundError(project.id)
        except ProjectNotFoundError:
            raise
        except Exception as e:
            raise ProjectError(f"Failed to update project: {e}") from e

        try:
            cursor.execute("BEGIN TRANSACTION;")
            
            project.updated_at = datetime.now(timezone.utc)
            
            cursor.execute(
                """
                UPDATE projects SET
                    workspace_id = ?,
                    name = ?,
                    root_path = ?,
                    repository_metadata_json = ?,
                    environment_variables_json = ?,
                    tags_json = ?,
                    provider_preference = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    project.workspace_id,
                    project.name,
                    project.root_path,
                    json.dumps(project.repository_metadata),
                    json.dumps(project.environment_variables),
                    json.dumps(project.tags),
                    project.provider_preference,
                    project.updated_at,
                    project.id
                )
            )
            conn.commit()
            return project
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ProjectError(f"Failed to update project: {e}") from e

    def delete(self, project_id: str) -> bool:
        """Deletes a project. Returns True if deleted, False if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (project_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ProjectError(f"Failed to delete project: {e}") from e

    def list(self, workspace_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Project]:
        """Lists projects with optional workspace filtering and pagination."""
        conn = self._get_connection()
        query = "SELECT * FROM projects"
        params = []
        if workspace_id:
            query += " WHERE workspace_id = ?"
            params.append(workspace_id)
        query += " ORDER BY name ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [self._row_to_project(row) for row in cursor.fetchall()]
