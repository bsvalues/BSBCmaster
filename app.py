"""
This module provides the FastAPI application instance for the MCP Assessor Agent API.
"""

# Import and expose the FastAPI app instance from the app package
from app import app

# This file is used by Uvicorn to run the FastAPI application
# It imports and exposes the app instance from the app package

# Make the app instance available at the module level
# This is what uvicorn will import when run with app:app
__all__ = ['app']