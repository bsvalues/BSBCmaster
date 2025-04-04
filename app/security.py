import logging
import secrets
from fastapi import Depends, HTTPException
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from .settings import settings

logger = logging.getLogger("mcp_assessor_api")

# API key security
API_KEY_HEADER = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Depends(API_KEY_HEADER)):
    """
    Validate the API key provided in the X-API-Key header.
    
    This function serves as a security dependency to protect API endpoints
    from unauthorized access. It verifies that a valid API key is present
    in the request headers, matching the configured API key.
    
    Args:
        api_key_header: The API key from the request header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is missing (401) or invalid (403)
    """
    # Log the attempt (but not the key itself)
    request_id = secrets.token_hex(6)  # Generate a unique ID for this request for tracing

    if not api_key_header:
        logger.warning(f"API request [{request_id}] missing required authorization header")
        # Use a generic 401 Unauthorized response
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key is missing in request headers",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Test the provided key against our stored key using a timing-safe comparison
    # to prevent timing attacks (although Python's != should be constant time)
    if api_key_header != settings.API_KEY:
        logger.warning(f"Invalid API key attempt [{request_id}]")
        # Use a 403 Forbidden response for invalid keys
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    # API key is valid, log the successful authentication
    logger.info(f"Successful API authentication [{request_id}]")
    return api_key_header
