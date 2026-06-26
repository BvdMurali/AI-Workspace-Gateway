"""
AI Workspace Gateway - Structured Logging Middleware
Logs HTTP requests and latency in structured JSON.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests."""

    def __init__(self, app, logger: getattr(logging, "Logger", None) = None) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger("gateway")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Avoid logging WebSocket connections in HTTP logger (they are logged in WS handler)
        if request.url.path == "/ws" or request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Retrieve request context
        request_id = getattr(request.state, "request_id", "unknown")
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"

        response = await call_next(request)

        status_code = response.status_code
        duration_ms = getattr(request.state, "duration_ms", 0.0)

        # Log structure
        log_payload = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "request_id": request_id,
            "correlation_id": correlation_id,
            "client_ip": client_ip,
        }

        # Select log level based on response code
        if status_code >= 500:
            self.logger.error(
                f"HTTP {request.method} {request.url.path} failed with {status_code}",
                extra=log_payload
            )
        elif status_code >= 400:
            self.logger.warning(
                f"HTTP {request.method} {request.url.path} returned client error {status_code}",
                extra=log_payload
            )
        else:
            self.logger.info(
                f"HTTP {request.method} {request.url.path} completed with {status_code}",
                extra=log_payload
            )

        return response
