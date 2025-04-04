"""
This module provides logging utilities for the FastAPI application.
"""

import logging
import time
from datetime import datetime
from typing import Callable, Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APILoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging API requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log API requests and responses."""
        # Generate request ID
        request_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(int(time.time() * 1000) % 1000)
        
        # Start timer
        start_time = time.time()
        
        # Extract request information
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log request
        logger.info(f"[{request_id}] Request: {method} {path} from {client_ip} - {user_agent}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"[{request_id}] Response: {response.status_code} - "
                f"took {execution_time:.4f}s - {method} {path}"
            )
            
            return response
        except Exception as e:
            # Log exception
            logger.error(
                f"[{request_id}] Exception: {str(e)} - "
                f"took {time.time() - start_time:.4f}s - {method} {path}"
            )
            # Re-raise exception
            raise