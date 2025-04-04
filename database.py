"""
This module provides the Flask routes for the MCP Assessor Agent API database interface.
"""

import datetime
import json
import os
import logging
import requests
from flask import render_template, request, jsonify, Blueprint, current_app
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a constant for the FastAPI URL if it's not in the environment
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# Import or define API settings with fallbacks
try:
    from app.settings import settings as fastapi_settings
    API_PREFIX = fastapi_settings.API_PREFIX
    API_KEY = fastapi_settings.API_KEY
except (ImportError, AttributeError):
    logger.warning("Could not import FastAPI settings, using defaults")
    API_PREFIX = "/api"
    API_KEY = os.environ.get("API_KEY", "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e")

# Get db instance from app_setup
from app_setup import db, app

# Create a Blueprint for database-related routes
database_bp = Blueprint('database', __name__)

@database_bp.route('/')
def index():
    """Render the index page with API documentation."""
    return render_template('index.html', title="MCP Assessor Agent API")

@database_bp.route('/api-docs')
def api_docs():
    """Proxy to FastAPI OpenAPI documentation."""
    # Note: FastAPI docs URL is configured in FastAPI setup with API_PREFIX
    # Get the base URL for FastAPI docs based on current settings
    from app.settings import settings as fastapi_settings
    docs_url = f"{FASTAPI_URL}{fastapi_settings.API_PREFIX}/docs"
    
    return render_template('api_docs.html', 
                         fastapi_url=FASTAPI_URL,
                         fastapi_docs_url=docs_url,
                         title="API Documentation")

@database_bp.route('/openapi.json')
def openapi_schema():
    """Proxy to FastAPI OpenAPI schema."""
    try:
        # Import settings to ensure we have the correct API prefix
        from app.settings import settings as fastapi_settings
        
        # The OpenAPI schema URL is relative to the API prefix
        # In FastAPI, the OpenAPI schema is at /openapi.json in relation to the base prefix
        # So we need to include the API_PREFIX in the URL
        openapi_url = f"{FASTAPI_URL}{fastapi_settings.API_PREFIX}/openapi.json"
        
        response = requests.get(openapi_url)
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Error fetching OpenAPI schema: {str(e)}")
        return jsonify({"error": f"Failed to fetch OpenAPI schema: {str(e)}"}), 500

@database_bp.route('/api/health')
def health_check():
    """Check the health of the API and its database connections."""
    try:
        # Import settings to get the correct API prefix
        from app.settings import settings as fastapi_settings
        
        # Check FastAPI health
        # Note: In FastAPI, health check may be at API_PREFIX/health or at root /health
        # Try both paths to ensure we can connect
        try:
            # First try with API_PREFIX
            response = requests.get(f"{FASTAPI_URL}{fastapi_settings.API_PREFIX}/health")
            api_health = response.json()
        except Exception:
            # If that fails, try the root health endpoint
            response = requests.get(f"{FASTAPI_URL}/health")
            api_health = response.json()
        
        # Check database connection through SQLAlchemy
        db_ok = False
        try:
            # Execute a simple query to test the connection
            db.session.execute(text('SELECT 1'))
            db_ok = True
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
        
        result = {
            "status": "success" if api_health.get("status") == "healthy" and db_ok else "error",
            "message": "API and database are operational" if db_ok else "Database connection issue",
            "database_status": {
                "flask_db": db_ok,
                "api_status": api_health.get("status", "error")
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "database_status": {"flask_db": False},
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500

@database_bp.route('/api/parcels')
def get_parcels():
    """Get a list of parcels with optional filtering."""
    try:
        # Extract query parameters
        city = request.args.get('city')
        state = request.args.get('state')
        year = request.args.get('year')
        
        # Import models
        from models import Parcel
        
        query = db.session.query(Parcel)
        
        if city:
            query = query.filter(Parcel.city.ilike(f"%{city}%"))
        if state:
            query = query.filter(Parcel.state == state)
        if year:
            query = query.filter(Parcel.assessment_year == int(year))
        
        # Execute query
        parcels = query.limit(100).all()
        
        # Convert to JSON-serializable format
        result = []
        for parcel in parcels:
            result.append({
                "id": parcel.id,
                "parcel_id": parcel.parcel_id,
                "address": parcel.address,
                "city": parcel.city,
                "state": parcel.state,
                "zip_code": parcel.zip_code,
                "total_value": float(parcel.total_value),
                "assessment_year": parcel.assessment_year
            })
        
        return jsonify({
            "status": "success",
            "count": len(result),
            "data": result
        })
    except Exception as e:
        logger.error(f"Error fetching parcels: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch parcels: {str(e)}"
        }), 500

@database_bp.route('/api/parcels/<parcel_id>')
def get_parcel(parcel_id):
    """Get detailed information about a specific parcel."""
    try:
        from models import Parcel, Property, Sale
        
        # Find the parcel
        parcel = db.session.query(Parcel).filter(Parcel.parcel_id == parcel_id).first()
        
        if not parcel:
            return jsonify({
                "status": "error",
                "message": f"Parcel with ID {parcel_id} not found"
            }), 404
        
        # Get related property details
        property_details = db.session.query(Property).filter(Property.parcel_id == parcel.id).all()
        properties = []
        for prop in property_details:
            properties.append({
                "id": prop.id,
                "property_type": prop.property_type,
                "year_built": prop.year_built,
                "square_footage": prop.square_footage,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "lot_size": prop.lot_size,
                "lot_size_unit": prop.lot_size_unit,
                "stories": prop.stories,
                "condition": prop.condition,
                "quality": prop.quality,
                "tax_district": prop.tax_district,
                "zoning": prop.zoning
            })
        
        # Get sales history
        sales_history = db.session.query(Sale).filter(Sale.parcel_id == parcel.id).all()
        sales = []
        for sale in sales_history:
            sales.append({
                "id": sale.id,
                "sale_date": sale.sale_date.isoformat(),
                "sale_price": float(sale.sale_price),
                "sale_type": sale.sale_type,
                "transaction_id": sale.transaction_id,
                "buyer_name": sale.buyer_name,
                "seller_name": sale.seller_name,
                "financing_type": sale.financing_type
            })
        
        # Build detailed response
        result = {
            "parcel": {
                "id": parcel.id,
                "parcel_id": parcel.parcel_id,
                "address": parcel.address,
                "city": parcel.city,
                "state": parcel.state,
                "zip_code": parcel.zip_code,
                "land_value": float(parcel.land_value),
                "improvement_value": float(parcel.improvement_value),
                "total_value": float(parcel.total_value),
                "assessment_year": parcel.assessment_year,
                "latitude": parcel.latitude,
                "longitude": parcel.longitude,
                "created_at": parcel.created_at.isoformat(),
                "updated_at": parcel.updated_at.isoformat()
            },
            "properties": properties,
            "sales_history": sales
        }
        
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        logger.error(f"Error fetching parcel details: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch parcel details: {str(e)}"
        }), 500

@database_bp.route('/api/schema')
def get_schema():
    """Get database schema details for parcels, properties, and sales tables."""
    try:
        schema = {
            "parcels": {
                "name": "parcels",
                "description": "Real estate parcel information (main assessment record)",
                "columns": [
                    {"name": "id", "type": "Integer", "primary_key": True, "description": "Primary key"},
                    {"name": "parcel_id", "type": "String(50)", "description": "Unique parcel identifier"},
                    {"name": "address", "type": "String(255)", "description": "Property street address"},
                    {"name": "city", "type": "String(100)", "description": "Property city"},
                    {"name": "state", "type": "String(50)", "description": "Property state"},
                    {"name": "zip_code", "type": "String(20)", "description": "Property postal code"},
                    {"name": "land_value", "type": "Numeric(12,2)", "description": "Assessed land value"},
                    {"name": "improvement_value", "type": "Numeric(12,2)", "description": "Assessed improvements value"},
                    {"name": "total_value", "type": "Numeric(12,2)", "description": "Total assessed value"},
                    {"name": "assessment_year", "type": "Integer", "description": "Year of assessment"},
                    {"name": "latitude", "type": "Float", "description": "Geographic latitude"},
                    {"name": "longitude", "type": "Float", "description": "Geographic longitude"},
                    {"name": "created_at", "type": "DateTime", "description": "Record creation timestamp"},
                    {"name": "updated_at", "type": "DateTime", "description": "Record update timestamp"}
                ]
            },
            "properties": {
                "name": "properties",
                "description": "Physical property characteristics",
                "columns": [
                    {"name": "id", "type": "Integer", "primary_key": True, "description": "Primary key"},
                    {"name": "parcel_id", "type": "Integer", "foreign_key": "parcels.id", "description": "Foreign key to parcels table"},
                    {"name": "property_type", "type": "String(50)", "description": "Type of property (residential, commercial, etc.)"},
                    {"name": "year_built", "type": "Integer", "description": "Year the property was constructed"},
                    {"name": "square_footage", "type": "Integer", "description": "Total building area in square feet"},
                    {"name": "bedrooms", "type": "Integer", "description": "Number of bedrooms"},
                    {"name": "bathrooms", "type": "Float", "description": "Number of bathrooms"},
                    {"name": "lot_size", "type": "Float", "description": "Size of the lot"},
                    {"name": "lot_size_unit", "type": "String(20)", "description": "Unit of measurement for lot size"},
                    {"name": "stories", "type": "Float", "description": "Number of stories"},
                    {"name": "condition", "type": "String(50)", "description": "Property condition rating"},
                    {"name": "quality", "type": "String(50)", "description": "Property quality rating"},
                    {"name": "tax_district", "type": "String(50)", "description": "Taxation district"},
                    {"name": "zoning", "type": "String(50)", "description": "Zoning classification"},
                    {"name": "created_at", "type": "DateTime", "description": "Record creation timestamp"},
                    {"name": "updated_at", "type": "DateTime", "description": "Record update timestamp"}
                ]
            },
            "sales": {
                "name": "sales",
                "description": "Property sale transaction history",
                "columns": [
                    {"name": "id", "type": "Integer", "primary_key": True, "description": "Primary key"},
                    {"name": "parcel_id", "type": "Integer", "foreign_key": "parcels.id", "description": "Foreign key to parcels table"},
                    {"name": "sale_date", "type": "Date", "description": "Date of property sale"},
                    {"name": "sale_price", "type": "Numeric(12,2)", "description": "Sale price"},
                    {"name": "sale_type", "type": "String(50)", "description": "Type of sale transaction"},
                    {"name": "transaction_id", "type": "String(50)", "description": "Unique transaction identifier"},
                    {"name": "buyer_name", "type": "String(255)", "description": "Name of buyer"},
                    {"name": "seller_name", "type": "String(255)", "description": "Name of seller"},
                    {"name": "financing_type", "type": "String(50)", "description": "Type of financing used"},
                    {"name": "created_at", "type": "DateTime", "description": "Record creation timestamp"},
                    {"name": "updated_at", "type": "DateTime", "description": "Record update timestamp"}
                ]
            }
        }
        
        return jsonify({
            "status": "success",
            "data": schema
        })
    except Exception as e:
        logger.error(f"Error fetching schema: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch schema: {str(e)}"
        }), 500

# Proxy routes for FastAPI endpoints
@database_bp.route('/api/run-query', methods=['POST'])
def proxy_run_query():
    """Proxy for the FastAPI run-query endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': request.headers.get('X-API-Key', API_KEY)
        }
        
        # Make sure we have valid JSON data
        data = request.json if request.is_json else {}
        
        # Log the request
        logger.info(f"Proxying request to FastAPI run-query: {FASTAPI_URL}{API_PREFIX}/run-query")
        
        # Try to connect to FastAPI service
        try:
            response = requests.post(
                f"{FASTAPI_URL}{API_PREFIX}/run-query",
                json=data,
                headers=headers,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Return the response from FastAPI
            return jsonify(response.json()), response.status_code
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to FastAPI service at {FASTAPI_URL}")
            return jsonify({
                "status": "error",
                "message": "Could not connect to the FastAPI service. Please check if it's running."
            }), 503  # Service Unavailable
            
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to FastAPI service")
            return jsonify({
                "status": "error",
                "message": "Request to FastAPI service timed out"
            }), 504  # Gateway Timeout
            
    except Exception as e:
        logger.error(f"Error proxying run-query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@database_bp.route('/api/nl-to-sql', methods=['POST'])
def proxy_nl_to_sql():
    """Proxy for the FastAPI natural language to SQL endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': request.headers.get('X-API-Key', API_KEY)
        }
        
        # Make sure we have valid JSON data
        data = request.json if request.is_json else {}
        
        # Log the request
        logger.info(f"Proxying request to FastAPI nl-to-sql: {FASTAPI_URL}{API_PREFIX}/nl-to-sql")
        
        # Try to connect to FastAPI service
        try:
            response = requests.post(
                f"{FASTAPI_URL}{API_PREFIX}/nl-to-sql",
                json=data,
                headers=headers,
                timeout=60  # Longer timeout because language model processing takes time
            )
            
            # Return the response from FastAPI
            return jsonify(response.json()), response.status_code
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to FastAPI service at {FASTAPI_URL}")
            return jsonify({
                "status": "error",
                "message": "Could not connect to the FastAPI service. Please check if it's running."
            }), 503  # Service Unavailable
            
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to FastAPI service")
            return jsonify({
                "status": "error",
                "message": "Request to FastAPI service timed out. NL to SQL conversion may take longer than expected."
            }), 504  # Gateway Timeout
            
    except Exception as e:
        logger.error(f"Error proxying nl-to-sql: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@database_bp.route('/api/discover-schema')
def proxy_discover_schema():
    """Proxy for the FastAPI schema discovery endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', API_KEY)
        }
        
        # Log the request
        logger.info(f"Proxying request to FastAPI discover-schema: {FASTAPI_URL}{API_PREFIX}/discover-schema")
        
        # Try to connect to FastAPI service
        try:
            response = requests.get(
                f"{FASTAPI_URL}{API_PREFIX}/discover-schema",
                params=request.args,
                headers=headers,
                timeout=30
            )
            
            # Return the response from FastAPI
            return jsonify(response.json()), response.status_code
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to FastAPI service at {FASTAPI_URL}")
            return jsonify({
                "status": "error",
                "message": "Could not connect to the FastAPI service. Please check if it's running."
            }), 503  # Service Unavailable
            
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to FastAPI service")
            return jsonify({
                "status": "error",
                "message": "Request to FastAPI service timed out"
            }), 504  # Gateway Timeout
            
    except Exception as e:
        logger.error(f"Error proxying discover-schema: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@database_bp.route('/api/schema-summary')
def proxy_schema_summary():
    """Proxy for the FastAPI schema summary endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', API_KEY)
        }
        
        # Log the request
        logger.info(f"Proxying request to FastAPI schema-summary: {FASTAPI_URL}{API_PREFIX}/schema-summary")
        
        # Try to connect to FastAPI service
        try:
            response = requests.get(
                f"{FASTAPI_URL}{API_PREFIX}/schema-summary",
                params=request.args,
                headers=headers,
                timeout=30
            )
            
            # Return the response from FastAPI
            return jsonify(response.json()), response.status_code
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to FastAPI service at {FASTAPI_URL}")
            return jsonify({
                "status": "error", 
                "message": "Could not connect to the FastAPI service. Please check if it's running."
            }), 503  # Service Unavailable
            
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to FastAPI service")
            return jsonify({
                "status": "error",
                "message": "Request to FastAPI service timed out"
            }), 504  # Gateway Timeout
            
    except Exception as e:
        logger.error(f"Error proxying schema-summary: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@database_bp.route('/api/parameterized-query', methods=['POST'])
def proxy_parameterized_query():
    """Proxy for the FastAPI parameterized query endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': request.headers.get('X-API-Key', API_KEY)
        }
        
        # Make sure we have valid JSON data
        data = request.json if request.is_json else {}
        
        # Log the request
        logger.info(f"Proxying request to FastAPI parameterized-query: {FASTAPI_URL}{API_PREFIX}/parameterized-query")
        
        # Try to connect to FastAPI service
        try:
            response = requests.post(
                f"{FASTAPI_URL}{API_PREFIX}/parameterized-query",
                json=data,
                headers=headers,
                timeout=30
            )
            
            # Return the response from FastAPI
            return jsonify(response.json()), response.status_code
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to FastAPI service at {FASTAPI_URL}")
            return jsonify({
                "status": "error",
                "message": "Could not connect to the FastAPI service. Please check if it's running."
            }), 503  # Service Unavailable
            
        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to FastAPI service")
            return jsonify({
                "status": "error",
                "message": "Request to FastAPI service timed out"
            }), 504  # Gateway Timeout
            
    except Exception as e:
        logger.error(f"Error proxying parameterized-query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500