"""
This module initializes the FastAPI application.
"""

import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# Record application start time for uptime calculation
start_time = time.time()

# Load environment variables from .env file
load_dotenv()

from app.api import router as api_router
from app.db import initialize_db, close_db_connections
from app.settings import settings
from app.logger import APILoggingMiddleware
from app.cache import get_cache_stats, invalidate_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fastapi.log"),
    ]
)
logger = logging.getLogger(__name__)

# Define error handler middleware
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # Log the error
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            
            # Return a JSON response
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": "An unexpected error occurred",
                    "detail": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# Add middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(APILoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Initializing API resources")
    try:
        await initialize_db()
        logger.info("Database connections initialized")
    except Exception as e:
        logger.error(f"Error initializing database connections: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down API resources")
    try:
        # Clean up database connections
        await close_db_connections()
        
        # Clear cache
        invalidate_cache()
        
        logger.info("Resources cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up resources: {str(e)}")

# Add middleware routes
@app.get("/api/stats/cache")
async def cache_stats():
    """Get cache statistics."""
    return get_cache_stats()

@app.post("/api/cache/invalidate")
async def invalidate_cache_route(
    prefix: str = None, 
    api_key: str = None
):
    """
    Invalidate cache entries.
    
    Args:
        prefix: Optional prefix to match cache keys
        api_key: API key for authentication
    """
    # Check authentication
    if api_key != settings.API_KEY:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Invalid API key"}
        )
    
    invalidate_cache(prefix)
    return {"status": "success", "message": f"Cache invalidated for prefix: {prefix if prefix else 'all'}"}

# Add simple root health check
@app.get("/health")
async def root_health_check():
    """Simple root health check endpoint."""
    uptime = time.time() - start_time
    return {
        "status": "healthy",
        "service": "MCP Assessor Agent API",
        "uptime_seconds": round(uptime),
        "time": datetime.utcnow().isoformat()
    }

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)