"""
AI Workspace Gateway - Resource Domain Exceptions
"""

from apps.gateway.utils.exceptions import GatewayError


class ResourceError(GatewayError):
    """Base exception for all resource-related errors."""
    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a resource cannot be found in the system."""
    def __init__(self, resource_id: str) -> None:
        super().__init__(
            message=f"Resource with ID '{resource_id}' was not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=404
        )


class ResourceValidationError(ResourceError):
    """Raised when resource validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_VALIDATION_FAILED",
            status_code=422
        )
