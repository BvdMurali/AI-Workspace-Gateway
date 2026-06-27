"""
AI Workspace Gateway - Workspace Repository
Handles SQLite persistence for workspaces.
"""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError, WorkspaceError, DuplicateWorkspaceNameError


class WorkspaceRepository:
    """Interfaces with the SQLite database to store and retrieve workspaces."""

    def __init__(self, storage_bootstrap: StorageBootstrap) -> None:
        self.storage = storage_bootstrap

    def _get_connection(self) -> sqlite3.Connection:
        if not self.storage.connection:
            raise WorkspaceError("Database connection is not open.")
        return self.storage.connection

    def _row_to_workspace(self, row: sqlite3.Row) -> Workspace:
        """Helper to map a SQLite Row to a Workspace object."""
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

        config_data = {}
        if row["config_json"]:
            try:
                config_data = json.loads(row["config_json"])
            except Exception:
                pass

        return Workspace(
            id=row["id"],
            name=row["name"],
            config=config_data,
            created_at=parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def create(self, workspace: Workspace) -> Workspace:
        """Persists a new workspace in the SQLite database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            
            # Check for duplicate name
            cursor.execute("SELECT 1 FROM workspaces WHERE name = ?;", (workspace.name,))
            if cursor.fetchone():
                raise DuplicateWorkspaceNameError(workspace.name)

            cursor.execute(
                """
                INSERT INTO workspaces (
                    id, name, config_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    workspace.id,
                    workspace.name,
                    json.dumps(workspace.config),
                    workspace.created_at,
                    workspace.updated_at
                )
            )
            conn.commit()
            return workspace
        except DuplicateWorkspaceNameError:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise WorkspaceError(f"Failed to persist workspace: {e}") from e

    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Retrieves a workspace by its unique ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspaces WHERE id = ?;", (workspace_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_workspace(row)

    def get_by_name(self, name: str) -> Optional[Workspace]:
        """Retrieves a workspace by its name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspaces WHERE name = ?;", (name,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_workspace(row)

    def update(self, workspace: Workspace) -> Workspace:
        """Updates an existing workspace."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (workspace.id,))
            if not cursor.fetchone():
                raise WorkspaceNotFoundError(workspace.id)
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            raise WorkspaceError(f"Failed to update workspace: {e}") from e

        try:
            cursor.execute("BEGIN TRANSACTION;")
            
            # Check if name is changing and causes duplicate
            cursor.execute("SELECT id FROM workspaces WHERE name = ?;", (workspace.name,))
            row = cursor.fetchone()
            if row and row["id"] != workspace.id:
                raise DuplicateWorkspaceNameError(workspace.name)

            workspace.updated_at = datetime.now(timezone.utc)
            
            cursor.execute(
                """
                UPDATE workspaces SET
                    name = ?,
                    config_json = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    workspace.name,
                    json.dumps(workspace.config),
                    workspace.updated_at,
                    workspace.id
                )
            )
            conn.commit()
            return workspace
        except DuplicateWorkspaceNameError:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise WorkspaceError(f"Failed to update workspace: {e}") from e

    def delete(self, workspace_id: str) -> bool:
        """Deletes a workspace. Returns True if deleted, False if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (workspace_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM workspaces WHERE id = ?;", (workspace_id,))
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise WorkspaceError(f"Failed to delete workspace: {e}") from e

    def list(self, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """Lists workspaces with pagination."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM workspaces ORDER BY name ASC LIMIT ? OFFSET ?;",
            (limit, offset)
        )
        return [self._row_to_workspace(row) for row in cursor.fetchall()]
