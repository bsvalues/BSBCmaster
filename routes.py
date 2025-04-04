"""
This module provides Flask routes for the MCP Assessor Agent API.
"""

import os
import logging
import requests
import datetime
from flask import render_template, jsonify, request, Blueprint
from models import Parcel, Property, Sale
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a constant for the FastAPI URL
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# Create Blueprint for API routes
api_routes = Blueprint('api_routes', __name__)

@api_routes.route('/')
def index():
    """Render the index page with API documentation."""
    return render_template('index.html', title="MCP Assessor Agent API")

@api_routes.route('/api-docs')
def api_docs():
    """Proxy to FastAPI OpenAPI documentation."""
    return render_template('api_docs.html', 
                         fastapi_url=FASTAPI_URL,
                         title="API Documentation")

@api_routes.route('/openapi.json')
def openapi_schema():
    """Proxy to FastAPI OpenAPI schema."""
    try:
        response = requests.get(f"{FASTAPI_URL}/openapi.json")
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Error fetching OpenAPI schema: {str(e)}")
        return jsonify({"error": "Failed to fetch OpenAPI schema"}), 500

@api_routes.route('/api/health')
def health_check():
    """Health check endpoint for the API."""
    try:
        # Check FastAPI health
        try:
            response = requests.get(f"{FASTAPI_URL}/health", timeout=2)
            api_health = response.json() if response.status_code == 200 else {"status": "error"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to FastAPI: {str(e)}")
            api_health = {"status": "error", "detail": str(e)}
        
        result = {
            "status": "operational",
            "flask_api": {"status": "running"},
            "fastapi_service": api_health,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500

# Proxy routes for FastAPI endpoints
@api_routes.route('/api/run-query', methods=['POST'])
def proxy_run_query():
    """Proxy for the FastAPI run-query endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.post(
            f"{FASTAPI_URL}/api/run-query",
            json=request.json,
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying run-query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@api_routes.route('/api/nl-to-sql', methods=['POST'])
def proxy_nl_to_sql():
    """Proxy for the FastAPI natural language to SQL endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.post(
            f"{FASTAPI_URL}/api/nl-to-sql",
            json=request.json,
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying nl-to-sql: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500