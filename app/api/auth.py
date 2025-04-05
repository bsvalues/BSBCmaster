"""
Authentication module for the MCP Assessor Agent API.

This module provides API key authentication for the API endpoints.
"""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader, APIKey
from starlette.status import HTTP_403_FORBIDDEN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Get API key from environment or use default for development
API_KEY = os.getenv("API_KEY", "dev-api-key-for-testing")
API_KEY_NAME = "X-API-Key"

# Create API key header validator
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key():
    """Get the API key from environment variable."""
    return API_KEY

def api_key_auth(api_key: str = Security(api_key_header)):
    """
    Validate the API key.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        bool: True if the API key is valid
        
    Raises:
        HTTPException: If the API key is invalid
    """
    if api_key == API_KEY:
        return True
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

@router.get("/verify-api-key")
async def verify_api_key(_: bool = Depends(api_key_auth)):
    """
    Verify that the provided API key is valid.
    
    Returns:
        Dict: A message indicating the API key is valid
    """
    return {"message": "API key is valid"}