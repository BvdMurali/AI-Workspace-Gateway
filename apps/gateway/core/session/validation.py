"""
AI Workspace Gateway - Session Validation
Provides validation rules for session initialization and updates.
"""

import uuid
from apps.gateway.core.session.models import Session, SessionState
from apps.gateway.core.session.exceptions import SessionValidationError


class SessionValidation:
    """Validator class to check constraints and schemas on sessions."""

    @classmethod
    def validate_create(cls, session: Session) -> None:
        """Validates session object parameters on creation."""
        # 1. Verify UUID formatting for id, workspace_id, project_id, and current_execution_id
        try:
            uuid.UUID(session.id)
        except ValueError:
            raise SessionValidationError(f"Session ID '{session.id}' is not a valid UUID.")

        try:
            uuid.UUID(session.workspace_id)
        except ValueError:
            raise SessionValidationError(f"Workspace ID '{session.workspace_id}' is not a valid UUID.")

        if session.project_id:
            try:
                uuid.UUID(session.project_id)
            except ValueError:
                raise SessionValidationError(f"Project ID '{session.project_id}' is not a valid UUID.")

        if session.current_execution_id:
            try:
                uuid.UUID(session.current_execution_id)
            except ValueError:
                raise SessionValidationError(f"Current Execution ID '{session.current_execution_id}' is not a valid UUID.")

        # 2. Verify name
        if not session.name or not session.name.strip():
            raise SessionValidationError("Session name cannot be empty.")
        if len(session.name) > 255:
            raise SessionValidationError("Session name cannot exceed 255 characters.")

        # 3. Verify connected_clients
        if not isinstance(session.connected_clients, list):
            raise SessionValidationError("Connected clients must be a list.")
        for client in session.connected_clients:
            if not isinstance(client, str):
                raise SessionValidationError("Connected client IDs must be strings.")

        # 4. Verify state
        if not isinstance(session.state, SessionState):
            try:
                SessionState(session.state)
            except ValueError:
                raise SessionValidationError(f"Invalid session state: {session.state}")
        
        # 5. Last activity check
        if not session.last_activity:
            raise SessionValidationError("Session last_activity timestamp is required.")
        
        if not session.created_at or not session.updated_at:
            raise SessionValidationError("Session created_at and updated_at timestamps are required.")
