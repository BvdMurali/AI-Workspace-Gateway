"""
AI Workspace Gateway - Request Timing Middleware
Measures processing duration and adds X-Response-Time-Ms header.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure processing time of HTTP requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Inject response time header
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        # Also store on state for logger middleware convenience
        request.state.duration_ms = duration_ms
        
        return response
