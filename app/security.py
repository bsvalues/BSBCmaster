import logging
from fastapi import Depends, HTTPException
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from .settings import settings

logger = logging.getLogger("mcp_assessor_api")

# API key security
API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)

async def get_api_key(api_key_header: str = Depends(API_KEY_HEADER)):
    """
    Validate the API key provided in the X-API-Key header.
    
    Args:
        api_key_header: The API key from the request header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if not api_key_header:
        logger.warning("API request missing key header")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key_header != settings.API_KEY:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key_header
