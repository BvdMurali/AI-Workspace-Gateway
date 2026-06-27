"""
AI Workspace Gateway - Session Repository
Handles SQLite persistence for sessions.
"""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.core.session.models import Session, SessionState
from apps.gateway.core.session.exceptions import SessionNotFoundError, SessionError


class SessionRepository:
    """Interfaces with the SQLite database to store and retrieve sessions."""

    def __init__(self, storage_bootstrap: StorageBootstrap) -> None:
        self.storage = storage_bootstrap

    def _get_connection(self) -> sqlite3.Connection:
        if not self.storage.connection:
            raise SessionError("Database connection is not open.")
        return self.storage.connection

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Helper to map a SQLite Row to a Session object."""
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

        clients = []
        if row["connected_clients_json"]:
            try:
                clients = json.loads(row["connected_clients_json"])
            except Exception:
                pass

        return Session(
            id=row["id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            name=row["name"],
            connected_clients=clients,
            current_execution_id=row["current_execution_id"],
            last_activity=parse_dt(row["last_activity"]) or datetime.now(timezone.utc),
            state=SessionState(row["state"]),
            created_at=parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def create(self, session: Session) -> Session:
        """Persists a new session in the SQLite database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            
            # Verify workspace exists
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (session.workspace_id,))
            if not cursor.fetchone():
                from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
                raise WorkspaceNotFoundError(session.workspace_id)

            # Verify project exists if project_id is provided
            if session.project_id:
                cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (session.project_id,))
                if not cursor.fetchone():
                    from apps.gateway.core.project.exceptions import ProjectNotFoundError
                    raise ProjectNotFoundError(session.project_id)

            cursor.execute(
                """
                INSERT INTO sessions (
                    id, workspace_id, name, created_at, updated_at,
                    project_id, connected_clients_json, current_execution_id, last_activity, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session.id,
                    session.workspace_id,
                    session.name,
                    session.created_at,
                    session.updated_at,
                    session.project_id,
                    json.dumps(session.connected_clients),
                    session.current_execution_id,
                    session.last_activity,
                    session.state.value
                )
            )
            conn.commit()
            return session
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if "Workspace with ID" in str(e) or "Project with ID" in str(e):
                raise
            raise SessionError(f"Failed to persist session: {e}") from e

    def get_by_id(self, session_id: str) -> Optional[Session]:
        """Retrieves a session by its unique ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def update(self, session: Session) -> Session:
        """Updates an existing session."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sessions WHERE id = ?;", (session.id,))
            if not cursor.fetchone():
                raise SessionNotFoundError(session.id)
        except SessionNotFoundError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to update session: {e}") from e

        try:
            cursor.execute("BEGIN TRANSACTION;")
            
            # Verify workspace exists
            cursor.execute("SELECT 1 FROM workspaces WHERE id = ?;", (session.workspace_id,))
            if not cursor.fetchone():
                from apps.gateway.core.workspace.exceptions import WorkspaceNotFoundError
                raise WorkspaceNotFoundError(session.workspace_id)

            # Verify project exists if project_id is provided
            if session.project_id:
                cursor.execute("SELECT 1 FROM projects WHERE id = ?;", (session.project_id,))
                if not cursor.fetchone():
                    from apps.gateway.core.project.exceptions import ProjectNotFoundError
                    raise ProjectNotFoundError(session.project_id)

            session.updated_at = datetime.now(timezone.utc)
            
            cursor.execute(
                """
                UPDATE sessions SET
                    workspace_id = ?,
                    name = ?,
                    updated_at = ?,
                    project_id = ?,
                    connected_clients_json = ?,
                    current_execution_id = ?,
                    last_activity = ?,
                    state = ?
                WHERE id = ?;
                """,
                (
                    session.workspace_id,
                    session.name,
                    session.updated_at,
                    session.project_id,
                    json.dumps(session.connected_clients),
                    session.current_execution_id,
                    session.last_activity,
                    session.state.value,
                    session.id
                )
            )
            conn.commit()
            return session
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            if "Workspace with ID" in str(e) or "Project with ID" in str(e):
                raise
            raise SessionError(f"Failed to update session: {e}") from e

    def delete(self, session_id: str) -> bool:
        """Deletes a session. Returns True if deleted, False if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sessions WHERE id = ?;", (session_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise SessionError(f"Failed to delete session: {e}") from e

    def list(
        self,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        state: Optional[SessionState] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Session]:
        """Lists sessions with optional filtering and pagination."""
        conn = self._get_connection()
        query = "SELECT * FROM sessions"
        conditions = []
        params = []

        if workspace_id:
            conditions.append("workspace_id = ?")
            params.append(workspace_id)
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if state:
            conditions.append("state = ?")
            params.append(state.value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [self._row_to_session(row) for row in cursor.fetchall()]
