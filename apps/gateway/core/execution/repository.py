"""
AI Workspace Gateway - Execution Repository
Handles SQLite persistence for executions, metadata, and events.
"""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.gateway.storage.bootstrap import StorageBootstrap
from apps.gateway.core.execution.models import Execution, ExecutionState, RetryPolicy
from apps.gateway.core.execution.exceptions import ExecutionNotFoundError, ExecutionError


class ExecutionRepository:
    """Interfaces with the SQLite database to store and retrieve executions."""

    def __init__(self, storage_bootstrap: StorageBootstrap) -> None:
        self.storage = storage_bootstrap

    def _get_connection(self) -> sqlite3.Connection:
        if not self.storage.connection:
            raise ExecutionError("Database connection is not open.")
        return self.storage.connection

    def _row_to_execution(self, row: sqlite3.Row, metadata: Dict[str, Any]) -> Execution:
        """Helper to map a SQLite Row and metadata dict to an Execution object."""
        # Helper to parse datetime safely
        def parse_dt(val: Any) -> Optional[datetime]:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
            try:
                # SQLite might return formatted string
                # E.g. "2026-06-26 14:05:07" or ISO format
                if " " in val:
                    dt = datetime.strptime(val.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                return None

        # Environment variables
        env_vars = {}
        if row["environment_variables_json"]:
            try:
                env_vars = json.loads(row["environment_variables_json"])
            except Exception:
                pass

        # Retry policy
        retry_policy_data = {}
        if row["retry_policy_json"]:
            try:
                retry_policy_data = json.loads(row["retry_policy_json"])
            except Exception:
                pass
        retry_policy = RetryPolicy.model_validate(retry_policy_data)

        # Tags
        tags = []
        if row["tags_json"]:
            try:
                tags = json.loads(row["tags_json"])
            except Exception:
                pass

        return Execution(
            id=row["id"],
            correlation_id=row["correlation_id"],
            workspace_id=row["workspace_id"],
            provider_id=row["provider_id"],
            tool_id=row["tool_id"],
            state=ExecutionState(row["state"]),
            priority=row["priority"],
            timeout=row["timeout"],
            retry_policy=retry_policy,
            owner=row["owner"],
            environment_variables=env_vars,
            metadata=metadata,
            tags=tags,
            created_at=parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
            scheduled_at=parse_dt(row["scheduled_at"]),
            completed_at=parse_dt(row["completed_at"]),
        )

    def _fetch_metadata(self, execution_id: str) -> Dict[str, Any]:
        """Fetches metadata key-value pairs for an execution."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key, value FROM execution_metadata WHERE execution_id = ?;",
            (execution_id,)
        )
        metadata = {}
        for row in cursor.fetchall():
            try:
                # Try parsing value as JSON if it represents a structured type
                metadata[row["key"]] = json.loads(row["value"])
            except Exception:
                metadata[row["key"]] = row["value"]
        return metadata

    def _save_metadata(self, conn: sqlite3.Connection, execution_id: str, metadata: Dict[str, Any]) -> None:
        """Saves metadata key-value pairs for an execution."""
        cursor = conn.cursor()
        # Clean existing metadata
        cursor.execute("DELETE FROM execution_metadata WHERE execution_id = ?;", (execution_id,))
        
        # Insert new metadata
        for k, v in metadata.items():
            # If value is a dict or list, serialize as JSON string
            if isinstance(v, (dict, list, bool)) or v is None:
                val_str = json.dumps(v)
            else:
                val_str = str(v)
            cursor.execute(
                "INSERT INTO execution_metadata (execution_id, key, value) VALUES (?, ?, ?);",
                (execution_id, k, val_str)
            )

    def create(self, execution: Execution) -> Execution:
        """Persists a new execution in the SQLite database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            
            cursor.execute(
                """
                INSERT INTO executions (
                    id, correlation_id, workspace_id, provider_id, tool_id, state, priority, timeout, owner,
                    environment_variables_json, retry_policy_json, tags_json, created_at, updated_at, scheduled_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    execution.id,
                    execution.correlation_id,
                    execution.workspace_id,
                    execution.provider_id,
                    execution.tool_id,
                    execution.state.value,
                    execution.priority,
                    execution.timeout,
                    execution.owner,
                    json.dumps(execution.environment_variables),
                    execution.retry_policy.model_dump_json(),
                    json.dumps(execution.tags),
                    execution.created_at,
                    execution.updated_at,
                    execution.scheduled_at,
                    execution.completed_at
                )
            )
            
            self._save_metadata(conn, execution.id, execution.metadata)
            
            conn.commit()
            return execution
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ExecutionError(f"Failed to persist execution: {e}") from e

    def get_by_id(self, execution_id: str) -> Optional[Execution]:
        """Retrieves an execution by its unique ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM executions WHERE id = ?;", (execution_id,))
        row = cursor.fetchone()
        if not row:
            return None
            
        metadata = self._fetch_metadata(execution_id)
        return self._row_to_execution(row, metadata)

    def update(self, execution: Execution) -> Execution:
        """Updates an existing execution's fields and metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM executions WHERE id = ?;", (execution.id,))
            if not cursor.fetchone():
                raise ExecutionNotFoundError(execution.id)
        except ExecutionNotFoundError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to update execution: {e}") from e

        try:
            cursor.execute("BEGIN TRANSACTION;")
            
            # Record current update timestamp
            execution.updated_at = datetime.now(timezone.utc)
            
            cursor.execute(
                """
                UPDATE executions SET
                    correlation_id = ?,
                    workspace_id = ?,
                    provider_id = ?,
                    tool_id = ?,
                    state = ?,
                    priority = ?,
                    timeout = ?,
                    owner = ?,
                    environment_variables_json = ?,
                    retry_policy_json = ?,
                    tags_json = ?,
                    updated_at = ?,
                    scheduled_at = ?,
                    completed_at = ?
                WHERE id = ?;
                """,
                (
                    execution.correlation_id,
                    execution.workspace_id,
                    execution.provider_id,
                    execution.tool_id,
                    execution.state.value,
                    execution.priority,
                    execution.timeout,
                    execution.owner,
                    json.dumps(execution.environment_variables),
                    execution.retry_policy.model_dump_json(),
                    json.dumps(execution.tags),
                    execution.updated_at,
                    execution.scheduled_at,
                    execution.completed_at,
                    execution.id
                )
            )
            
            self._save_metadata(conn, execution.id, execution.metadata)
            
            conn.commit()
            return execution
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ExecutionError(f"Failed to update execution: {e}") from e

    def delete(self, execution_id: str) -> bool:
        """Deletes an execution from the database. Returns True if deleted, False if not found."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM executions WHERE id = ?;", (execution_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM executions WHERE id = ?;", (execution_id,))
            conn.commit()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ExecutionError(f"Failed to delete execution: {e}") from e

    def list(
        self,
        state: Optional[ExecutionState] = None,
        workspace_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Execution]:
        """Lists executions with optional filtering by state and workspace."""
        conn = self._get_connection()
        query = "SELECT * FROM executions"
        conditions = []
        params = []

        if state:
            conditions.append("state = ?")
            params.append(state.value)
        if workspace_id:
            conditions.append("workspace_id = ?")
            params.append(workspace_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        
        executions = []
        for row in cursor.fetchall():
            metadata = self._fetch_metadata(row["id"])
            executions.append(self._row_to_execution(row, metadata))
        return executions

    def search(
        self,
        query_params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[Execution]:
        """
        Searches executions based on fields, tags, correlation IDs, or metadata keys.
        Supports query params:
          - correlation_id: exact match
          - workspace_id: exact match
          - provider_id: exact match
          - tool_id: exact match
          - state: exact match / list
          - owner: exact match
          - tag: checks if tag exists in tags
          - metadata_key: matches executions having this metadata key
          - metadata_value: matches metadata_key with this value
        """
        conn = self._get_connection()
        query = "SELECT DISTINCT e.* FROM executions e"
        joins = []
        conditions = []
        params = []

        # If searching by metadata key/value, we join the execution_metadata table
        meta_key = query_params.get("metadata_key")
        meta_val = query_params.get("metadata_value")
        if meta_key or meta_val:
            joins.append("LEFT JOIN execution_metadata m ON e.id = m.execution_id")
            if meta_key:
                conditions.append("m.key = ?")
                params.append(meta_key)
            if meta_val:
                # Check for exact string match or JSON string match
                conditions.append("(m.value = ? OR m.value = ?)")
                params.extend([str(meta_val), json.dumps(meta_val)])

        # Handle other filters
        for field in ["correlation_id", "workspace_id", "provider_id", "tool_id", "owner"]:
            if query_params.get(field):
                conditions.append(f"e.{field} = ?")
                params.append(query_params[field])

        # State filter
        state_param = query_params.get("state")
        if state_param:
            if isinstance(state_param, list):
                placeholders = ",".join(["?"] * len(state_param))
                conditions.append(f"e.state IN ({placeholders})")
                params.extend([s.value if isinstance(s, ExecutionState) else s for s in state_param])
            else:
                conditions.append("e.state = ?")
                params.append(state_param.value if isinstance(state_param, ExecutionState) else state_param)

        # Tag filter (JSON array contains query_tag)
        tag_param = query_params.get("tag")
        if tag_param:
            # Simple SQLite JSON contains check using LIKE since SQLite JSON1 is standard but syntax varies.
            # E.g. tags_json LIKE '%"tag_param"%'
            conditions.append("e.tags_json LIKE ?")
            params.append(f'%"{tag_param}"%')

        if joins:
            query += " " + " ".join(joins)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY e.created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        
        executions = []
        for row in cursor.fetchall():
            metadata = self._fetch_metadata(row["id"])
            executions.append(self._row_to_execution(row, metadata))
        return executions

    def save_event(self, execution_id: str, event_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Records an execution event in the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute(
                """
                INSERT INTO execution_events (id, execution_id, event_type, payload_json)
                VALUES (?, ?, ?, ?);
                """,
                (event_id, execution_id, event_type, json.dumps(payload))
            )
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise ExecutionError(f"Failed to record execution event: {e}") from e

    def get_events(self, execution_id: str) -> List[Dict[str, Any]]:
        """Retrieves all events recorded for a given execution in chronological order."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, event_type, payload_json, timestamp FROM execution_events WHERE execution_id = ? ORDER BY timestamp ASC;",
            (execution_id,)
        )
        events = []
        for row in cursor.fetchall():
            try:
                payload = json.loads(row["payload_json"])
            except Exception:
                payload = {}
            events.append({
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": payload,
                "timestamp": row["timestamp"]
            })
        return events

    def get_next_queued(self, now: datetime) -> Optional[Execution]:
        """Retrieves the next queued execution based on priority and scheduling timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM executions
            WHERE state = ? AND (scheduled_at IS NULL OR scheduled_at <= ?)
            ORDER BY priority DESC, created_at ASC
            LIMIT 1;
            """,
            (ExecutionState.QUEUED.value, now)
        )
        row = cursor.fetchone()
        if not row:
            return None
            
        metadata = self._fetch_metadata(row["id"])
        return self._row_to_execution(row, metadata)
