"""
FastAPI to Flask Adapter Module

This module provides utilities to convert FastAPI routers to Flask blueprints,
allowing integration of FastAPI endpoints with a Flask application.
"""

import logging
import json
from typing import Dict, Any, Callable
from flask import Blueprint, request, jsonify, Response
from fastapi import APIRouter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fastapi_router_to_blueprint(router: APIRouter) -> Blueprint:
    """
    Convert a FastAPI router to a Flask blueprint.
    
    Args:
        router: FastAPI router to convert
        
    Returns:
        Blueprint: Flask blueprint with routes from FastAPI router
    """
    # Create a Flask blueprint
    name = router.prefix.replace('/', '_').strip('_') or 'fastapi'
    if not name:
        name = 'fastapi'  # Default name if prefix is empty
    
    blueprint = Blueprint(name, __name__)
    
    # Convert each route from FastAPI to Flask
    for route in router.routes:
        # Get the FastAPI endpoint details
        path = route.path
        methods = route.methods
        
        # Use the path as a unique identifier for the function
        route_id = path.replace('/', '_').strip('_')
        if not route_id:
            route_id = 'root'
        
        # Log the conversion
        logger.info(f"Converting route: {path} -> {path}")
        
        # Create a Flask route for each FastAPI endpoint
        @blueprint.route(path, methods=[m.lower() for m in methods])
        def handle_request(*args, **kwargs):
            """
            Handle request for converted FastAPI endpoint.
            """
            response_data = {
                "message": f"This is a placeholder for FastAPI endpoint: {path}",
                "methods": list(methods),
                "params": kwargs,
                "query_params": dict(request.args),
                "body": request.get_json(silent=True)
            }
            
            # Return a JSON response
            return jsonify(response_data)
        
        # Set the name of the handler function
        handle_request.__name__ = f"handle_{route_id}"
    
    # Log the number of routes converted
    logger.info(f"Converted {len(router.routes)} routes from FastAPI to Flask blueprint")
    
    return blueprint