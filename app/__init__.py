"""
This module initializes the FastAPI application with all routes and middleware.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from app.settings import Settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()
    
    # Create FastAPI app with versioned endpoint prefix
    app = FastAPI(
        title=settings.APP_NAME,
        description="A secure API for efficient database querying with real estate focus.",
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Connect to databases on startup
    @app.on_event("startup")
    async def startup_db_clients():
        """Initialize database connections on startup."""
        from app.db import initialize_db
        await initialize_db()
    
    # Close database connections on shutdown
    @app.on_event("shutdown")
    async def shutdown_db_clients():
        """Close database connections on shutdown."""
        from app.db import close_db_connections
        await close_db_connections()
    
    # Import and include API routes
    from app.api import router as api_router
    app.include_router(api_router)
    
    return app