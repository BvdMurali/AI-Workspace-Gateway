"""
AI Workspace Gateway - FastAPI Application Factory
Sets up middleware, mounts routers, and binds lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.gateway.routers.health import router as health_router


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
        lifespan=lifespan
    )
    
    app.state.lifecycle = lifecycle
    app.state.container = lifecycle.container
    
    # Configure CORS middleware
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
    
    # Mount health endpoints at root and under api/v1
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api/v1")
    
    return app
