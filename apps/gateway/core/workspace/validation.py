"""
AI Workspace Gateway - Workspace Validation
Provides validation rules for workspace initialization and updates.
"""

import uuid
from apps.gateway.core.workspace.models import Workspace
from apps.gateway.core.workspace.exceptions import WorkspaceValidationError


class WorkspaceValidation:
    """Validator class to check constraints and schemas on workspaces."""

    @classmethod
    def validate_create(cls, workspace: Workspace) -> None:
        """Validates workspace object parameters on creation."""
        # 1. Verify UUID formatting for id if provided
        try:
            uuid.UUID(workspace.id)
        except ValueError:
            raise WorkspaceValidationError(f"Workspace ID '{workspace.id}' is not a valid UUID.")

        # 2. Verify name
        if not workspace.name or not workspace.name.strip():
            raise WorkspaceValidationError("Workspace name cannot be empty.")
        if len(workspace.name) > 255:
            raise WorkspaceValidationError("Workspace name cannot exceed 255 characters.")

        # 3. Verify config is a dictionary
        if not isinstance(workspace.config, dict):
            raise WorkspaceValidationError("Workspace config must be a dictionary.")
        for k in workspace.config.keys():
            if not isinstance(k, str):
                raise WorkspaceValidationError("Workspace config keys must be strings.")
