"""
This module provides security functionality for the API.
"""

from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from app.settings import Settings

settings = Settings()

# Define the API key security scheme
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate the API key provided in the request header.
    
    Args:
        api_key_header: The API key from the request header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if not api_key_header:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Missing API Key. Please include your API key in the '{settings.API_KEY_HEADER_NAME}' header"
        )
    
    if api_key_header != settings.API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Invalid API Key. Please check your API key and try again."
        )
    
    return api_key_header