"""
AI Workspace Gateway - FastAPI Application Factory
Sets up middleware, mounts routers, and binds lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.exceptions import RequestValidationError

from apps.gateway.routers.health import router as legacy_health_router
from apps.gateway.routers.v1.health import router as v1_health_router
from apps.gateway.routers.v1.executions import router as v1_executions_router
from apps.gateway.routers.websocket import router as ws_router

from apps.gateway.middleware.request_id import RequestIdMiddleware
from apps.gateway.middleware.timing import TimingMiddleware
from apps.gateway.middleware.logging import StructuredLoggingMiddleware
from apps.gateway.middleware.security import SecurityHeadersMiddleware
from apps.gateway.middleware.rate_limit import RateLimiterMiddleware
from apps.gateway.middleware.recovery import (
    RecoveryMiddleware,
    gateway_error_handler,
    validation_error_handler,
    general_exception_handler
)
from apps.gateway.utils.exceptions import GatewayError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events using the Lifecycle manager."""
    lifecycle = app.state.lifecycle
    await lifecycle.startup()
    yield
    await lifecycle.shutdown()


def create_app(lifecycle: Any) -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    app = FastAPI(
        title="AI Workspace Gateway",
        description="Local-first agentic workspace gateway runtime core.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,   # We define custom docs/redoc routes at root
        redoc_url=None,
        openapi_url=None
    )
    
    app.state.lifecycle = lifecycle
    app.state.container = lifecycle.container
    
    # ------------------------------------------------------------------
    # Middleware Registration Sequence
    # (Middlewares added later wrap those added earlier)
    # ------------------------------------------------------------------
    
    # 1. GZip Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 2. CORS Middleware
    config = lifecycle.config
    server_config = config.get("server", {})
    cors_origins = server_config.get("corsOrigins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 3. Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Rate Limiting (inner limit check)
    rate_limit_capacity = server_config.get("rateLimitCapacity", 100)
    rate_limit_period = server_config.get("rateLimitPeriodSeconds", 60)
    app.add_middleware(
        RateLimiterMiddleware,
        capacity=rate_limit_capacity,
        period_seconds=rate_limit_period
    )
    
    # 5. Structured Request Logging
    app.add_middleware(StructuredLoggingMiddleware)
    
    # 6. Request Execution Timing
    app.add_middleware(TimingMiddleware)
    
    # 7. Recovery (outer exception catcher)
    app.add_middleware(RecoveryMiddleware)
    
    # 8. Request & Correlation ID Tracer (outermost state generator)
    app.add_middleware(RequestIdMiddleware)
    
    # ------------------------------------------------------------------
    # Global Exception Handlers
    # ------------------------------------------------------------------
    app.add_exception_handler(GatewayError, gateway_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # ------------------------------------------------------------------
    # Versioning Sub-App Setup (v1)
    # ------------------------------------------------------------------
    v1_app = FastAPI(
        title="AI Workspace Gateway v1",
        description="Version 1 of the AI Workspace Gateway Communication API.",
        version="1.0.0",
        openapi_url="/openapi",
        docs_url=None,
        redoc_url=None
    )
    v1_app.state.lifecycle = lifecycle
    v1_app.state.container = lifecycle.container
    
    # Register exception handlers on sub-app to handle route exceptions correctly
    v1_app.add_exception_handler(GatewayError, gateway_error_handler)
    v1_app.add_exception_handler(RequestValidationError, validation_error_handler)
    v1_app.add_exception_handler(Exception, general_exception_handler)
    
    # Mount v1 routers
    v1_app.include_router(v1_health_router)
    v1_app.include_router(v1_executions_router, prefix="/executions", tags=["Executions"])
    
    # Mount the v1 sub-app under /api/v1
    app.mount("/api/v1", v1_app)
    
    # ------------------------------------------------------------------
    # Main App Routers (Root level)
    # ------------------------------------------------------------------
    # Backwards compatible legacy endpoints at root
    app.include_router(legacy_health_router)
    
    # Expose WebSocket at root exactly: /ws
    app.include_router(ws_router)
    
    # ------------------------------------------------------------------
    # API Documentation Routes (Docs & Redoc)
    # ------------------------------------------------------------------
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Serves custom Swagger UI pointing to the version 1 OpenAPI schema."""
        return get_swagger_ui_html(
            openapi_url="/api/v1/openapi",
            title="AI Workspace Gateway - Swagger UI"
        )
        
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        """Serves custom Redoc pointing to the version 1 OpenAPI schema."""
        return get_redoc_html(
            openapi_url="/api/v1/openapi",
            title="AI Workspace Gateway - Redoc"
        )
        
    @app.get("/api/v1/openapi", include_in_schema=False)
    async def get_v1_openapi(request: Request):
        """Returns the OpenAPI JSON representation of the version 1 API."""
        # Directly serve the sub-app's openapi JSON
        return v1_app.openapi()
        
    return app
