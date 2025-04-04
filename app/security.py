"""
This module provides security utilities for the FastAPI application.
"""

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST

from app.settings import settings
from app.validators import is_valid_sql_query, validate_natural_language_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define API key authentication
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)

# Rate limit tracking
# Structure: {client_ip: {endpoint: [timestamp, ...]}}
_rate_limit_store: Dict[str, Dict[str, List[float]]] = {}

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

def extract_parameters(query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract named parameters from a SQL query and replace them with placeholders.
    
    Args:
        query: SQL query string with parameters like :param_name
        
    Returns:
        Tuple of (parameterized_query, params_dict)
    """
    # Find all parameters with format :param_name
    param_matches = re.findall(r':(\w+)', query)
    params = {}
    
    # Replace direct parameter values with parameterized placeholders
    parameterized_query = query
    for param_name in param_matches:
        params[param_name] = None  # Initialize with None, will be filled by caller
        # No need to replace in the query as most DB drivers understand :param_name format
    
    return parameterized_query, params

def verify_sql_query(query: str, allow_write: bool = False) -> Dict[str, Any]:
    """
    Verify and validate SQL query for security issues.
    
    Args:
        query: SQL query string
        allow_write: Whether to allow write operations
        
    Returns:
        Dict with validation results and parameterized query
    """
    # Basic SQL validation
    validation_result = is_valid_sql_query(query)
    
    # If not valid, return the validation result
    if not validation_result["valid"]:
        return validation_result
    
    # Check for write operations if not allowed
    if not allow_write:
        write_operations = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        for op in write_operations:
            if re.search(rf'\b{op}\b', query, re.IGNORECASE):
                validation_result["valid"] = False
                validation_result["issues"].append(f"Write operation {op} not allowed")
                validation_result["severity"] = "high"
                return validation_result
    
    # Extract parameters
    parameterized_query, params = extract_parameters(query)
    
    # Add to validation result
    validation_result["parameterized_query"] = parameterized_query
    validation_result["parameters"] = params
    
    return validation_result

def check_rate_limit(request: Request, endpoint_name: str) -> Optional[Dict[str, Any]]:
    """
    Check if the request is rate limited.
    
    Args:
        request: FastAPI Request object
        endpoint_name: Name of the endpoint
        
    Returns:
        None if not rate limited, or a dict with error details if rate limited
    """
    # If rate limiting is disabled, return None
    if not settings.RATE_LIMIT.ENABLED:
        return None
    
    # Check for API key to bypass rate limiting if configured
    try:
        api_key = request.headers.get(settings.API_KEY_HEADER_NAME)
        if settings.RATE_LIMIT.BYPASS_RATE_LIMIT_WITH_API_KEY and api_key == settings.API_KEY:
            # API key is valid, bypass rate limiting
            return None
    except Exception:
        # If API key check fails, continue with rate limiting
        pass
    
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Initialize rate limit tracking for this client if needed
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = {}
    
    endpoint_key = endpoint_name if settings.RATE_LIMIT.BY_ENDPOINT else "global"
    
    # Initialize endpoint tracking for this client if needed
    if endpoint_key not in _rate_limit_store[client_ip]:
        _rate_limit_store[client_ip][endpoint_key] = []
    
    # Remove timestamps outside the time window
    _rate_limit_store[client_ip][endpoint_key] = [
        ts for ts in _rate_limit_store[client_ip][endpoint_key]
        if ts > now - settings.RATE_LIMIT.TIME_WINDOW
    ]
    
    # Check if the number of requests within the time window exceeds the limit
    if len(_rate_limit_store[client_ip][endpoint_key]) >= settings.RATE_LIMIT.DEFAULT_RATE:
        # Calculate retry-after
        oldest_timestamp = min(_rate_limit_store[client_ip][endpoint_key])
        retry_after = int(oldest_timestamp + settings.RATE_LIMIT.TIME_WINDOW - now)
        retry_after = max(1, retry_after)  # Ensure at least 1 second
        
        return {
            "status_code": 429,
            "detail": f"Too many requests. Try again in {retry_after} seconds.",
            "headers": {"Retry-After": str(retry_after)}
        }
    
    # Record this request
    _rate_limit_store[client_ip][endpoint_key].append(now)
    
    return None

def validate_nl_query(
    nl_query: str,
    min_length: int = 3,
    max_length: int = 1000
) -> Dict[str, Any]:
    """
    Validate a natural language query.
    
    Args:
        nl_query: Natural language query string
        min_length: Minimum length of the query
        max_length: Maximum length of the query
        
    Returns:
        Dict with validation results
    """
    # Check length
    if len(nl_query) < min_length:
        return {
            "valid": False,
            "issues": [f"Query too short (minimum {min_length} characters)"],
            "severity": "low"
        }
    
    if len(nl_query) > max_length:
        return {
            "valid": False,
            "issues": [f"Query too long (maximum {max_length} characters)"],
            "severity": "medium"
        }
    
    # Validate content
    return validate_natural_language_prompt(nl_query)