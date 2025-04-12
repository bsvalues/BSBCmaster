"""
Demo routes for JWT authentication.

This module provides example routes that are protected by JWT authentication.
These routes are for demonstration purposes only.
"""

from flask import Blueprint, jsonify, g
from app.auth.protect import auth_required, permission_required, agent_type_required

# Create blueprint
demo_routes = Blueprint('auth_demo', __name__)

@demo_routes.route('/api/auth/demo/public', methods=['GET'])
def public_route():
    """
    Public route that doesn't require authentication.
    """
    return jsonify({
        "status": "success",
        "message": "This is a public endpoint that anyone can access.",
        "requires_auth": False
    })

@demo_routes.route('/api/auth/demo/protected', methods=['GET'])
@auth_required
def protected_route():
    """
    Protected route that requires authentication.
    """
    # Access user data from g.user (added by auth_required decorator)
    username = g.user.get("sub", "Unknown User")
    roles = g.user.get("roles", [])
    
    return jsonify({
        "status": "success",
        "message": f"Hello, {username}! You have successfully accessed a protected endpoint.",
        "requires_auth": True,
        "user_data": {
            "username": username,
            "roles": roles
        }
    })

@demo_routes.route('/api/auth/demo/admin', methods=['GET'])
@permission_required("manage:users")
def admin_route():
    """
    Admin route that requires the manage:users permission.
    """
    username = g.user.get("sub", "Unknown Admin")
    
    return jsonify({
        "status": "success",
        "message": f"Hello, Admin {username}! You have successfully accessed an admin-only endpoint.",
        "requires_auth": True,
        "requires_permission": "manage:users"
    })

@demo_routes.route('/api/auth/demo/assessor', methods=['GET'])
@permission_required("write:assessment")
def assessor_route():
    """
    Assessor route that requires the write:assessment permission.
    """
    username = g.user.get("sub", "Unknown Assessor")
    
    return jsonify({
        "status": "success",
        "message": f"Hello, Assessor {username}! You have successfully accessed an assessor-only endpoint.",
        "requires_auth": True,
        "requires_permission": "write:assessment"
    })

@demo_routes.route('/api/auth/demo/valuation-agent', methods=['GET'])
@agent_type_required("valuation")
def valuation_agent_route():
    """
    Route that requires a valuation agent.
    """
    agent_id = g.user.get("agent_id", "Unknown Agent")
    
    return jsonify({
        "status": "success",
        "message": f"Hello, Valuation Agent {agent_id}! You have successfully accessed a valuation-agent-only endpoint.",
        "requires_auth": True,
        "requires_agent_type": "valuation"
    })

# Function to register routes with the Flask app
def register_auth_demo_routes(app):
    """
    Register the authentication demo routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(demo_routes)