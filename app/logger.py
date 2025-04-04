"""
This module provides logging utilities for the API.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Create logger for this module
logger = logging.getLogger(__name__)

# Define log levels for different API operations
LOG_LEVELS = {
    "query": logging.INFO,
    "schema": logging.DEBUG,
    "health": logging.DEBUG,
    "error": logging.ERROR,
    "security": logging.WARNING,
    "cache": logging.DEBUG,
}

def log_api_call(
    operation: str,
    message: str,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None,
    execution_time: Optional[float] = None,
):
    """
    Log API call with structured data.
    
    Args:
        operation: Type of operation (query, schema, health, error, security)
        message: Log message
        request_data: Optional request data
        response_data: Optional response data
        error: Optional exception
        execution_time: Optional execution time in seconds
    """
    log_level = LOG_LEVELS.get(operation, logging.INFO)
    
    # Create structured log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "message": message,
    }
    
    # Add additional data if available
    if request_data:
        # Mask sensitive data
        if "api_key" in request_data:
            request_data["api_key"] = "********"
        log_entry["request"] = request_data
    
    if response_data:
        log_entry["response"] = response_data
    
    if error:
        log_entry["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    
    if execution_time is not None:
        log_entry["execution_time"] = execution_time
    
    # Log as JSON string
    logger.log(log_level, json.dumps(log_entry))

class APILoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging API requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a request ID
        request_id = str(int(time.time() * 1000))
        
        # Start timing
        start_time = time.time()
        
        # Capture request details
        request_details = {
            "id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown",
            "headers": dict(request.headers),
        }
        
        # Try to parse request body for POST/PUT requests
        if request.method in ["POST", "PUT"]:
            try:
                # Clone the request body to avoid consuming it
                body = await request.body()
                # Reconstruct the request with the body
                if body:
                    try:
                        request_details["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        request_details["body"] = "non-JSON body"
            except Exception as e:
                logger.warning(f"Failed to parse request body: {str(e)}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log the request and response
            log_api_call(
                operation="request",
                message=f"{request.method} {request.url.path} - {response.status_code}",
                request_data=request_details,
                response_data={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                },
                execution_time=execution_time,
            )
            
            return response
        except Exception as e:
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log the error
            log_api_call(
                operation="error",
                message=f"Error processing {request.method} {request.url.path}",
                request_data=request_details,
                error=e,
                execution_time=execution_time,
            )
            
            # Re-raise the exception
            raise