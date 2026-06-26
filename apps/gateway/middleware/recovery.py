"""
AI Workspace Gateway - Exception Recovery Middleware
Catches unhandled exceptions, maps them, and returns structured JSON responses.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from apps.gateway.utils.exceptions import map_exception, GatewayError


class RecoveryMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions in the request pipeline,
    logging the details and returning a structured JSON error response.
    """

    def __init__(self, app, logger: getattr(logging, "Logger", None) = None) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger("gateway")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            self.logger.critical(
                f"Unhandled exception during HTTP request to '{request.url.path}': {exc}",
                exc_info=True,
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "correlation_id": getattr(request.state, "correlation_id", "unknown"),
                    "path": request.url.path
                }
            )
            mapped = map_exception(exc)
            
            # Format according to ERROR_MODEL.md flat response recommended format
            return JSONResponse(
                status_code=mapped.status_code,
                content={
                    "code": mapped.code,
                    "message": mapped.message,
                    "details": mapped.details
                },
                headers={
                    "X-Request-ID": getattr(request.state, "request_id", "unknown"),
                    "X-Correlation-ID": getattr(request.state, "correlation_id", "unknown")
                }
            )


async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """FastAPI exception handler for custom GatewayErrors."""
    logger = logging.getLogger("gateway")
    logger.error(
        f"Gateway error occurred: [{exc.code}] {exc.message}",
        extra={
            "code": exc.code,
            "request_id": getattr(request.state, "request_id", "unknown"),
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            "details": exc.details
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        },
        headers={
            "X-Request-ID": getattr(request.state, "request_id", "unknown"),
            "X-Correlation-ID": getattr(request.state, "correlation_id", "unknown")
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI exception handler for RequestValidationErrors."""
    mapped = map_exception(exc)
    return JSONResponse(
        status_code=mapped.status_code,
        content={
            "code": mapped.code,
            "message": mapped.message,
            "details": mapped.details
        },
        headers={
            "X-Request-ID": getattr(request.state, "request_id", "unknown"),
            "X-Correlation-ID": getattr(request.state, "correlation_id", "unknown")
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler for generic unhandled exceptions."""
    logger = logging.getLogger("gateway")
    logger.critical(
        f"Generic unhandled error caught: {exc}",
        exc_info=True,
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "correlation_id": getattr(request.state, "correlation_id", "unknown")
        }
    )
    mapped = map_exception(exc)
    return JSONResponse(
        status_code=mapped.status_code,
        content={
            "code": mapped.code,
            "message": mapped.message,
            "details": mapped.details
        },
        headers={
            "X-Request-ID": getattr(request.state, "request_id", "unknown"),
            "X-Correlation-ID": getattr(request.state, "correlation_id", "unknown")
        }
    )
