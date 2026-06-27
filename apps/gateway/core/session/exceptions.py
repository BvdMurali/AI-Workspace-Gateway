"""
AI Workspace Gateway - Session Domain Exceptions
"""

from apps.gateway.utils.exceptions import GatewayError


class SessionError(GatewayError):
    """Base exception for all session-related errors."""
    pass


class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found in the system."""
    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Session with ID '{session_id}' was not found.",
            code="SESSION_NOT_FOUND",
            status_code=404
        )


class SessionValidationError(SessionError):
    """Raised when session validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="SESSION_VALIDATION_FAILED",
            status_code=422
        )
