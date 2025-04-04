"""
This module provides rate limiting for API endpoints.
"""

import logging
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter data structures
# Structure: {client_ip: [(timestamp, endpoint), ...]}
_request_history: Dict[str, List[Tuple[float, str]]] = defaultdict(list)

def rate_limit(
    max_requests: int = 100,
    time_window: int = 60,
    by_endpoint: bool = False
) -> Callable:
    """
    Rate limiter decorator for API endpoints.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
        by_endpoint: Whether to apply rate limiting per endpoint
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path if by_endpoint else "global"
            
            # Check rate limit
            if is_rate_limited(client_ip, endpoint, max_requests, time_window):
                # Log rate limit violation
                logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
                # Return 429 Too Many Requests
                retry_after = get_retry_after(client_ip, endpoint, max_requests, time_window)
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Record request
            record_request(client_ip, endpoint)
            
            # Execute the function
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator

def is_rate_limited(
    client_ip: str,
    endpoint: str,
    max_requests: int,
    time_window: int
) -> bool:
    """
    Check if the client is rate limited.
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
        
    Returns:
        True if rate limited, False otherwise
    """
    # Clean up old requests
    cleanup_old_requests(client_ip, time_window)
    
    # Get requests within time window
    relevant_requests = get_relevant_requests(client_ip, endpoint)
    
    # Check if limit is exceeded
    return len(relevant_requests) >= max_requests

def record_request(client_ip: str, endpoint: str):
    """
    Record a new request.
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint
    """
    _request_history[client_ip].append((time.time(), endpoint))

def cleanup_old_requests(client_ip: str, time_window: int):
    """
    Clean up old requests outside the time window.
    
    Args:
        client_ip: Client IP address
        time_window: Time window in seconds
    """
    if client_ip not in _request_history:
        return
    
    cutoff_time = time.time() - time_window
    _request_history[client_ip] = [
        req for req in _request_history[client_ip]
        if req[0] >= cutoff_time
    ]

def get_relevant_requests(client_ip: str, endpoint: str) -> List[Tuple[float, str]]:
    """
    Get requests for the given endpoint or all endpoints if endpoint is 'global'.
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint or 'global'
        
    Returns:
        List of relevant requests
    """
    if client_ip not in _request_history:
        return []
    
    if endpoint == "global":
        return _request_history[client_ip]
    else:
        return [req for req in _request_history[client_ip] if req[1] == endpoint]

def get_retry_after(
    client_ip: str,
    endpoint: str,
    max_requests: int,
    time_window: int
) -> int:
    """
    Calculate how many seconds until the client can make another request.
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
        
    Returns:
        Seconds until the client can make another request
    """
    relevant_requests = get_relevant_requests(client_ip, endpoint)
    
    if not relevant_requests or len(relevant_requests) < max_requests:
        return 0
    
    # Sort by timestamp (oldest first)
    sorted_requests = sorted(relevant_requests, key=lambda x: x[0])
    
    # The oldest request that should be removed to allow a new request
    oldest_request_to_expire = sorted_requests[-(max_requests)][0]
    
    # Calculate when this request will expire
    expiry_time = oldest_request_to_expire + time_window
    
    # Calculate seconds until expiry
    seconds_until_expiry = max(1, int(expiry_time - time.time()))
    
    return seconds_until_expiry