"""
AI Workspace Gateway - Workspace Domain Exceptions
"""

from apps.gateway.utils.exceptions import GatewayError


class WorkspaceError(GatewayError):
    """Base exception for all workspace-related errors."""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace cannot be found in the system."""
    def __init__(self, workspace_id: str) -> None:
        super().__init__(
            message=f"Workspace with ID '{workspace_id}' was not found.",
            code="WORKSPACE_NOT_FOUND",
            status_code=404
        )


class WorkspaceValidationError(WorkspaceError):
    """Raised when workspace validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="WORKSPACE_VALIDATION_FAILED",
            status_code=422
        )


class DuplicateWorkspaceNameError(WorkspaceError):
    """Raised when a workspace name already exists."""
    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"Workspace with name '{name}' already exists.",
            code="DUPLICATE_WORKSPACE_NAME",
            status_code=409
        )
