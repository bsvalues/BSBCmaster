"""
Authentication Protection Middleware for Flask Routes

This module provides decorators and middleware functions to protect Flask routes 
with JWT authentication and permission checks.
"""

import logging
from functools import wraps
from flask import request, jsonify, current_app, g
from app.auth.jwt import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_token_from_header():
    """
    Extract JWT token from the Authorization header.
    
    Returns:
        str or None: The token if found, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    # Check if header is in the format "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]

def decode_token(token):
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        dict: Decoded token payload if valid, None otherwise
    """
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Token validation error: {str(e)}")
        return None

def auth_required(f):
    """
    Decorator to require authentication for a route.
    
    This decorator checks for a valid JWT token in the Authorization header
    and adds the decoded token payload to g.user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from header
        token = get_token_from_header()
        if not token:
            return jsonify({
                "status": "error", 
                "message": "Missing authentication token"
            }), 401
        
        # Decode and validate token
        payload = decode_token(token)
        if not payload:
            return jsonify({
                "status": "error", 
                "message": "Invalid or expired token"
            }), 401
        
        # Store user/agent data in g for route handlers to use
        g.user = payload
        
        # Continue to route handler
        return f(*args, **kwargs)
    
    return decorated

def permission_required(permission):
    """
    Decorator to require a specific permission for a route.
    
    This decorator first checks for authentication using auth_required,
    then checks if the authenticated user has the specified permission.
    
    Args:
        permission: The permission required to access the route
    """
    def decorator(f):
        @wraps(f)
        @auth_required
        def decorated(*args, **kwargs):
            # Check if user has the required permission
            user_permissions = g.user.get("permissions", [])
            
            # Check for permission or admin access
            if permission not in user_permissions and "read:all" not in user_permissions:
                return jsonify({
                    "status": "error", 
                    "message": f"Permission denied: {permission} required"
                }), 403
            
            # Continue to route handler
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator

def agent_type_required(agent_type):
    """
    Decorator to require a specific agent type for a route.
    
    This decorator is specifically for protecting routes that should only
    be accessible to certain types of MCP agents.
    
    Args:
        agent_type: The type of agent required to access the route
    """
    def decorator(f):
        @wraps(f)
        @auth_required
        def decorated(*args, **kwargs):
            # Check if token is for an agent (sub starts with "agent:")
            sub = g.user.get("sub", "")
            if not sub.startswith("agent:"):
                return jsonify({
                    "status": "error", 
                    "message": "This endpoint requires an agent token"
                }), 403
            
            # Check agent type
            if g.user.get("agent_type") != agent_type:
                return jsonify({
                    "status": "error", 
                    "message": f"This endpoint requires a {agent_type} agent"
                }), 403
            
            # Continue to route handler
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator


# Example usage in a Flask route:
"""
@app.route('/api/protected', methods=['GET'])
@auth_required
def protected_route():
    # Access user data from g.user
    username = g.user.get("sub")
    return jsonify({"message": f"Hello, {username}!"})

@app.route('/api/admin-only', methods=['GET'])
@permission_required("manage:users")
def admin_only_route():
    return jsonify({"message": "Welcome, admin!"})

@app.route('/api/valuation-only', methods=['POST'])
@agent_type_required("valuation")
def valuation_only_route():
    return jsonify({"message": "Valuation agent request processed"})
"""