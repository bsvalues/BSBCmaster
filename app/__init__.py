"""
Main FastAPI application module.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="MCP Assessor Agent API",
    description="API for the Benton County Assessor's Office AI Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register authentication routes
try:
    from app.auth.routes import router as auth_router
    app.include_router(auth_router, prefix="/api/v1", tags=["authentication"])
    logger.info("Authentication routes registered successfully")
except ImportError as e:
    logger.error(f"Failed to import authentication routes: {e}")

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for the API."""
    return {
        "status": "success",
        "message": "API is operational",
        "api_version": "1.0.0"
    }

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MCP Assessor Agent API",
        "version": "1.0.0",
        "description": "API for the Benton County Assessor's Office AI Platform"
    }