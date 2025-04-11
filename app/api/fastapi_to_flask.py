"""
FastAPI to Flask Adapter

This module provides functionality to convert FastAPI routes to Flask blueprints,
enabling the integration of FastAPI endpoints into a Flask application.
"""

import logging
import json
from typing import Any, Dict, List, Callable
from flask import Blueprint, request, jsonify, Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fastapi_router_to_blueprint(fastapi_router) -> Blueprint:
    """
    Convert a FastAPI router to a Flask blueprint.
    
    Args:
        fastapi_router: FastAPI router/APIRouter object
        
    Returns:
        Flask blueprint with equivalent routes
    """
    # Extract prefix and tags from FastAPI router
    prefix = fastapi_router.prefix
    tags = fastapi_router.tags[0] if fastapi_router.tags else "api"
    
    # Create Flask blueprint
    blueprint_name = tags.lower().replace(' ', '_')
    blueprint = Blueprint(blueprint_name, __name__, url_prefix=prefix)
    
    logger.info(f"Converting FastAPI router with prefix '{prefix}' to Flask blueprint '{blueprint_name}'")
    
    # Map FastAPI routes to Flask routes
    for route in fastapi_router.routes:
        path = route.path.replace(prefix, '')  # Remove prefix from path
        path = path.replace('{', '<').replace('}', '>')  # Convert path params
        methods = route.methods
        
        logger.info(f"Converting route: {route.path} -> {prefix}{path}")
        
        # Create Flask route function
        def create_flask_route(fastapi_handler, path_template):
            def flask_route(*args, **kwargs):
                try:
                    # Get request data
                    request_data = {}
                    if request.method in ('POST', 'PUT', 'PATCH'):
                        if request.is_json:
                            request_data = request.get_json()
                        else:
                            try:
                                request_data = request.form.to_dict()
                            except Exception:
                                pass
                    
                    # Combine path params and query params
                    for key, value in request.args.items():
                        if key not in kwargs:
                            kwargs[key] = value
                    
                    # Prepare parameters for FastAPI handler
                    if request_data:
                        result = fastapi_handler(**request_data, **kwargs)
                    else:
                        result = fastapi_handler(**kwargs)
                    
                    # Convert response to Flask response
                    if isinstance(result, dict) or isinstance(result, list):
                        return jsonify(result)
                    else:
                        # For complex Pydantic models returned by FastAPI
                        try:
                            return jsonify(result.dict())
                        except AttributeError:
                            return str(result)
                
                except Exception as e:
                    logger.error(f"Error in converted route {path_template}: {str(e)}")
                    return jsonify({
                        "error": str(e),
                        "detail": f"Error in converted route {path_template}: {str(e)}"
                    }), 500
            
            # Set a unique name for the route function
            endpoint_name = f"{route.name}_{','.join(methods)}"
            flask_route.__name__ = endpoint_name
            return flask_route
        
        # Register the route with the blueprint
        blueprint.route(
            path, 
            methods=methods,
            endpoint=route.name
        )(create_flask_route(route.endpoint, path))
    
    logger.info(f"Converted {len(fastapi_router.routes)} routes from FastAPI to Flask blueprint")
    return blueprint