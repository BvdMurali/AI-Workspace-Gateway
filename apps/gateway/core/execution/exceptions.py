"""
AI Workspace Gateway - Execution Framework Exceptions
"""

from apps.gateway.utils.exceptions import GatewayError


class ExecutionError(GatewayError):
    """Base exception for all execution-related errors."""
    pass


class ExecutionNotFoundError(ExecutionError):
    """Raised when an execution cannot be found in the system."""
    def __init__(self, execution_id: str) -> None:
        super().__init__(
            message=f"Execution with ID '{execution_id}' was not found.",
            code="EXECUTION_NOT_FOUND",
            status_code=404
        )


class InvalidStateTransitionError(ExecutionError):
    """Raised when a state transition violates validation rules."""
    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(
            message=f"Invalid execution state transition from '{from_state}' to '{to_state}'.",
            code="INVALID_STATE_TRANSITION",
            status_code=400
        )


class ExecutionValidationError(ExecutionError):
    """Raised when execution parameters or metadata schema validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="EXECUTION_VALIDATION_FAILED",
            status_code=422
        )
