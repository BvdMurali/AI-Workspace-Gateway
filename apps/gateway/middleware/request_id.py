"""
AI Workspace Gateway - Request & Correlation ID Middleware
Extracts or generates request/correlation IDs for request tracing.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request and correlation IDs into the request state and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Resolve Request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        # Resolve Correlation ID (falls back to Request ID if missing)
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = request_id

        # Attach to request state for access inside other middlewares and routers
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        response = await call_next(request)

        # Append to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        return response
