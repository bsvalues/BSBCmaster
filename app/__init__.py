from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from .settings import settings
from .db import initialize_db, close_db_connections
import logging

logger = logging.getLogger("mcp_assessor_api")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="MCP Assessor Agent API",
        description="API for accessing and querying assessment data from MS SQL Server and PostgreSQL databases",
        version="1.0.0",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Add database initialization and cleanup events
    @app.on_event("startup")
    async def startup_db_clients():
        await initialize_db()
    
    @app.on_event("shutdown")
    async def shutdown_db_clients():
        await close_db_connections()
    
    # Import and include API routes
    from .api import router
    app.include_router(router)
    
    return app
