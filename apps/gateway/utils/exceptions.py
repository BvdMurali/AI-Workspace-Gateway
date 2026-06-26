"""
AI Workspace Gateway - Unified Exceptions Framework
Defines the base GatewayError and maps system exceptions to HTTP and WS errors.
"""

from typing import Any, Dict, Optional


class GatewayError(Exception):
    """Base exception class for all custom runtime gateway exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


class WorkspaceError(GatewayError):
    """Isolation violations, lock status errors, or missing workspaces."""
    
    def __init__(
        self,
        message: str,
        code: str = "WORKSPACE_ERROR",
        status_code: int = 400,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class ProviderError(GatewayError):
    """Auth, context overflow, or rate limit errors from model providers."""
    
    def __init__(
        self,
        message: str,
        code: str = "PROVIDER_ERROR",
        status_code: int = 502,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class ToolError(GatewayError):
    """Validation failures, timeout, or execution crash during tool invocation."""
    
    def __init__(
        self,
        message: str,
        code: str = "TOOL_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class HostError(GatewayError):
    """Keychain access, file path traversal, or host system issues."""
    
    def __init__(
        self,
        message: str,
        code: str = "HOST_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class StorageError(GatewayError):
    """SQLite corruption, full disk, or transaction lock errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class ConfigurationError(GatewayError):
    """Invalid default or environment configuration YAML schemas."""
    
    def __init__(
        self,
        message: str,
        code: str = "CONFIGURATION_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class AuthenticationError(GatewayError):
    """JWT/Bearer token invalid or missing errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "AUTH_TOKEN_INVALID",
        status_code: int = 401,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class NetworkError(GatewayError):
    """Gateway backend timeout, DNS resolution, or connectivity failures."""
    
    def __init__(
        self,
        message: str,
        code: str = "NETWORK_ERROR",
        status_code: int = 504,
        retryable: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class ValidationError(GatewayError):
    """Incorrect HTTP body parameters or payload formats."""
    
    def __init__(
        self,
        message: str,
        code: str = "REQUEST_BODY_INVALID",
        status_code: int = 422,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


class TaskError(GatewayError):
    """Poisoned queue items, task cancellation, or abort errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "TASK_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code, status_code, retryable, details)


def map_exception(exc: Exception) -> GatewayError:
    """
    Translates standard libraries and internal exceptions into unified GatewayErrors
    following ERROR_MODEL.md guidelines.
    """
    if isinstance(exc, GatewayError):
        return exc

    # Avoid circular import by checking class name string or local imports
    class_name = exc.__class__.__name__
    
    if class_name == "RequestValidationError":
        # FastAPI validation errors
        errors = getattr(exc, "errors", lambda: [])()
        return ValidationError(
            message="Request body or query parameters validation failed.",
            code="REQUEST_BODY_INVALID",
            details={"errors": errors}
        )

    if class_name == "StorageError":
        # Existing StorageError mapping
        msg = str(exc)
        if "disk" in msg.lower() or "space" in msg.lower():
            return StorageError(
                message=msg,
                code="DISK_SPACE_EXHAUSTED",
                status_code=507
            )
        return StorageError(
            message=msg,
            code="DATABASE_ERROR",
            status_code=500
        )

    if class_name == "ConfigurationError":
        return ConfigurationError(
            message=str(exc),
            code="CONFIGURATION_ERROR"
        )

    if isinstance(exc, (ValueError, TypeError)):
        return ValidationError(
            message=str(exc),
            code="REQUEST_BODY_INVALID"
        )

    if isinstance(exc, TimeoutError):
        return NetworkError(
            message="Request timed out.",
            code="PROVIDER_CONNECT_TIMEOUT"
        )

    # General fallback
    return GatewayError(
        message=str(exc),
        code="INTERNAL_SERVER_ERROR",
        status_code=500
    )
