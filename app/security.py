"""
This module provides security utilities for the FastAPI application.
"""

import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define API key authentication
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)

def get_api_key(
    api_key_header: str = Security(api_key_header),
) -> str:
    """
    Validate the API key.
    
    Args:
        api_key_header: The API key from the request header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if api_key_header is None:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid API key in the header.",
        )
    
    if len(api_key_header) < settings.API_KEY_MIN_LENGTH:
        logger.warning(f"API key too short: {len(api_key_header)} chars")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"API key must be at least {settings.API_KEY_MIN_LENGTH} characters.",
        )
    
    if api_key_header != settings.API_KEY:
        # Log the first few characters of the incorrect key for debugging
        masked_key = f"{api_key_header[:4]}****"
        logger.warning(f"Invalid API key: {masked_key}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key. Please provide a valid API key.",
        )
    
    return api_key_header