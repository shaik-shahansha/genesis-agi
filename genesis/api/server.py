"""
FastAPI server for Genesis Minds.

Provides REST API and WebSocket endpoints for web/mobile apps.
"""

import os
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from genesis.config import get_settings
from genesis.api import routes
from genesis.api import marketplace_routes
from genesis.api import environment_routes

# Conditionally import multimodal if not disabled
DISABLE_MULTIMODAL = os.getenv("DISABLE_MULTIMODAL", "false").lower() == "true"
if not DISABLE_MULTIMODAL:
    try:
        from genesis.api import multimodal_routes
    except ImportError:
        DISABLE_MULTIMODAL = True
        multimodal_routes = None
else:
    multimodal_routes = None

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    print("[STARTUP] Genesis API server starting...")
    yield
    # Shutdown
    print("[SHUTDOWN] Genesis API server shutting down...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Genesis AGI API",
        description="API for creating and interacting with digital beings",
        version="0.1.5",
        lifespan=lifespan,
    )

    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add CORS middleware with preflight caching
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Mount static files for avatars and generated images
    avatars_dir = settings.data_dir / "avatars"
    generated_dir = settings.data_dir / "generated"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    
    app.mount("/avatars", StaticFiles(directory=str(avatars_dir)), name="avatars")
    app.mount("/generated", StaticFiles(directory=str(generated_dir)), name="generated")

    # Include routers
    app.include_router(routes.auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(routes.minds_router, prefix="/api/v1/minds", tags=["Minds"])
    app.include_router(routes.system_router, prefix="/api/v1/system", tags=["System"])
    app.include_router(routes.metaverse_router, prefix="/api/v1/metaverse", tags=["Metaverse"])
    app.include_router(routes.settings_router, prefix="/api/v1/settings", tags=["Settings"])
    app.include_router(marketplace_routes.router, prefix="/api/v1/marketplace", tags=["Marketplace"])
    app.include_router(environment_routes.router, prefix="/api/v1/environments", tags=["Environments"])
    # Admin endpoints (global admin management and admin-only actions)
    app.include_router(routes.admin_router, prefix="/api/v1/admin", tags=["Admin"])    
    # Include multimodal routes only if enabled
    if not DISABLE_MULTIMODAL and multimodal_routes:
        app.include_router(multimodal_routes.router, prefix="/api/v1/multimodal", tags=["Multimodal"])

    @app.get("/")
    @limiter.limit("10/minute")
    async def root(request: Request):
        return {
            "name": "Genesis AGI API",
            "version": "0.1.5",
            "status": "running",
            "documentation": "/docs",
            "authentication": "/api/v1/auth/token",
        }

    @app.get("/health")
    @limiter.limit("30/minute")
    async def health_check(request: Request):
        """Health check endpoint."""
        from genesis.models.orchestrator import ModelOrchestrator

        orchestrator = ModelOrchestrator()
        provider_health = await orchestrator.health_check()

        return {
            "status": "healthy",
            "providers": provider_health,
        }

    return app


def run_server(host: str = None, port: int = None, reload: bool = None):
    """Run the API server."""
    app = create_app()

    uvicorn.run(
        app,
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=reload if reload is not None else settings.api_reload,
    )


if __name__ == "__main__":
    run_server()
