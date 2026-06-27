"""
AI Workspace Gateway - Project Domain Exceptions
"""

from apps.gateway.utils.exceptions import GatewayError


class ProjectError(GatewayError):
    """Base exception for all project-related errors."""
    pass


class ProjectNotFoundError(ProjectError):
    """Raised when a project cannot be found in the system."""
    def __init__(self, project_id: str) -> None:
        super().__init__(
            message=f"Project with ID '{project_id}' was not found.",
            code="PROJECT_NOT_FOUND",
            status_code=404
        )


class ProjectValidationError(ProjectError):
    """Raised when project validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="PROJECT_VALIDATION_FAILED",
            status_code=422
        )
