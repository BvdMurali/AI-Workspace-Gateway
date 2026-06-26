"""
AI Workspace Gateway - Rate Limiting Middleware
Applies token-bucket rate limiting based on client IP or Client-ID.
"""

import time
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response
from apps.gateway.utils.exceptions import ProviderError


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory Token Bucket rate limiting middleware.
    Tracks requests per Client-ID header or Client IP.
    """

    def __init__(
        self,
        app,
        capacity: int = 100,
        period_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.capacity = capacity
        self.period = period_seconds
        self.fill_rate = capacity / period_seconds
        
        # Maps client_id/ip -> (tokens, last_update_time)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def _get_client_key(self, request: Request) -> str:
        """Determines the rate limiting key for the client."""
        # Use Client-ID header if present
        client_id = request.headers.get("Client-ID")
        if client_id:
            return f"client:{client_id}"
            
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
            
        return "anonymous"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bypass rate limiting for WebSocket upgrade handshake (it can have its own validation)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        client_key = self._get_client_key(request)
        now = time.time()

        # Dynamically retrieve configuration values if available
        capacity = self.capacity
        period = self.period
        
        lifecycle = getattr(request.app.state, "lifecycle", None)
        if lifecycle and lifecycle.config:
            server_config = lifecycle.config.get("server", {})
            capacity = server_config.get("rateLimitCapacity", self.capacity)
            period = server_config.get("rateLimitPeriodSeconds", self.period)

        fill_rate = capacity / period

        # Retrieve or initialize bucket
        if client_key not in self._buckets:
            tokens = float(capacity)
            last_update = now
        else:
            tokens, last_update = self._buckets[client_key]
            
            # Refill tokens based on elapsed time
            elapsed = now - last_update
            refill = elapsed * fill_rate
            tokens = min(float(capacity), tokens + refill)
            last_update = now

        # Evaluate token presence
        if tokens >= 1.0:
            tokens -= 1.0
            self._buckets[client_key] = (tokens, last_update)
        else:
            self._buckets[client_key] = (tokens, last_update)
            # Quota exceeded
            raise ProviderError(
                message="API rate limit exceeded. Please try again later.",
                code="PROVIDER_RATE_LIMIT",
                status_code=429
            )

        return await call_next(request)
