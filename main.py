"""
This file provides a combined server for both Flask documentation and backend services.
It serves as the main entry point for the application in Replit.
"""

import os
import sys

# Add app directory to path for imports

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sys
import signal
import logging
import threading
import subprocess
import time
import json
import datetime
import re
from sqlalchemy import func, text
import requests
from urllib.parse import urlparse
from flask import jsonify, request, Blueprint, render_template
from app.api.realtime import realtime_api
import map_module

from app_setup import app, db, create_tables
from routes import api_routes
from models import Parcel, Property, Sale, Account, PropertyImage
from app.db import execute_parameterized_query, parse_for_parameters, get_connection_string
from app.nl_processing import sql_to_natural_language, extract_query_intent
from sqlalchemy import create_engine, inspect
from app.validators import validate_query

# Import authentication modules
try:
    from app.auth.routes import router as auth_router
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import authentication routes: {e}")

# Import statistics routes
try:
    from app.api.statistics_routes import statistics_api
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import statistics API routes: {e}")

# Import data quality routes
try:
    from data_quality.api import router as data_quality_api
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import data quality API routes: {e}")

# Import minimalist routes
try:
    from routes_minimal import register_minimalist_routes
    # Register minimalist routes
    register_minimalist_routes(app)
    logger = logging.getLogger(__name__)
    logger.info("Minimalist design routes registered successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import minimalist routes: {e}")

# Register routes
app.register_blueprint(api_routes)

# Register authentication routes
try:
    # Convert FastAPI router to Flask blueprint
    from app.api.fastapi_to_flask import fastapi_router_to_blueprint
    auth_blueprint = fastapi_router_to_blueprint(auth_router)
    app.register_blueprint(auth_blueprint)
    logger.info("Authentication API routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register authentication API routes: {e}")

# Register statistics API routes
try:
    app.register_blueprint(statistics_api)
    logger.info("Statistics API routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register statistics API routes: {e}")

# Register data quality API routes
try:
    from fastapi import APIRouter
    # Convert FastAPI router to Flask blueprint
    from app.api.fastapi_to_flask import fastapi_router_to_blueprint
    data_quality_blueprint = fastapi_router_to_blueprint(data_quality_api)
    app.register_blueprint(data_quality_blueprint)
    logger.info("Data Quality API routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register data quality API routes: {e}")

# Register valuation API routes
try:
    # Import valuation API router
    from app.api.valuation import router as valuation_api
    # Convert FastAPI router to Flask blueprint
    valuation_blueprint = fastapi_router_to_blueprint(valuation_api)
    app.register_blueprint(valuation_blueprint)
    logger.info("Valuation API routes registered successfully")
except Exception as e:
    logger.error(f"Failed to register valuation API routes: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FASTAPI_PORT = 8000
FLASK_PORT = 5000

def seed_database_if_needed():
    """Seed the database if it's empty."""
    from import_attached_data import import_all_data
    # Check if we have any data
    with app.app_context():
        try:
            # Try to query the accounts table using the Account model
            count = db.session.query(Account).count()
            
            if count == 0:
                logger.info("No data found in accounts table, importing sample data")
                import_all_data()
            else:
                logger.info(f"Found {count} records in accounts table, skipping import")
                
        except Exception as e:
            logger.info(f"Tables may not exist yet: {str(e)}")
            logger.info("Creating tables and importing sample data")
            create_tables()
            import_all_data()

def start_fastapi():
    """Start the FastAPI service in a background thread."""
    logger.info("Starting FastAPI service...")
    
    # We'll run the fastapi server in a separate process
    fastapi_process = None
    
    def run_server():
        """Run uvicorn server in a separate process."""
        nonlocal fastapi_process
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "asgi:app", 
            "--host", "0.0.0.0", 
            "--port", str(FASTAPI_PORT),
            "--reload"
        ]
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor and log FastAPI output
        for line in fastapi_process.stdout:
            logger.info(f"[FastAPI] {line.strip()}")
            
        # If we get here, the process has terminated
        logger.info("FastAPI process exited with code {}".format(
            fastapi_process.returncode if fastapi_process else "unknown"
        ))
    
    # Start FastAPI in a background thread
    fastapi_thread = threading.Thread(target=run_server)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    
    # Wait for FastAPI to start
    logger.info("Waiting for FastAPI to start...")
    for i in range(60):  # Wait up to 60 seconds
        try:
            response = requests.get(f"http://localhost:{FASTAPI_PORT}/health")
            if response.status_code == 200:
                logger.info("FastAPI started successfully")
                return fastapi_process
        except requests.exceptions.ConnectionError as e:
            logger.info(f"Waiting for FastAPI to start (attempt {i+1}/60): {str(e)}")
            time.sleep(1)
    
    logger.warning("Timed out waiting for FastAPI to start")
    logger.error("Failed to start FastAPI")
    return fastapi_process

def cleanup_on_exit(signum=None, frame=None):
    """Cleanup resources on exit."""
    logger.info("Shutting down MCP Assessor Agent API server...")
    # Perform any cleanup here as needed
    logger.info("Shutdown complete")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# API endpoints for imported data
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint for the API."""
    try:
        with app.app_context():
            # Check database connection using ORM query
            db.session.query(Account).limit(1).all()  # Just run a simple query
            db_status = True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = False
    
    return jsonify({
        "status": "success" if db_status else "error",
        "message": "API is operational" if db_status else "Database connection failed",
        "database_status": {"postgres": db_status},
        "api_version": "1.0.0",
        "uptime": 0  # We don't track this currently
    })

@app.route('/api/imported-data/accounts', methods=['GET'])
def get_imported_accounts():
    """Get a list of imported accounts."""
    with app.app_context():
        try:
            # Get query parameters
            offset = request.args.get('offset', 0, type=int)
            limit = request.args.get('limit', 100, type=int)
            owner_name = request.args.get('owner_name', '')
            
            # Build query
            query = Account.query
            
            # Apply filters
            if owner_name:
                query = query.filter(Account.owner_name.ilike(f"%{owner_name}%"))
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            accounts = query.offset(offset).limit(limit).all()
            
            # Convert to dictionary
            account_list = []
            for account in accounts:
                account_dict = {
                    "id": account.id,
                    "account_id": account.account_id,
                    "owner_name": account.owner_name,
                    "property_address": account.property_address,
                    "property_city": account.property_city,
                    "mailing_address": account.mailing_address,
                    "mailing_city": account.mailing_city,
                    "mailing_state": account.mailing_state,
                    "mailing_zip": account.mailing_zip,
                    "legal_description": account.legal_description,
                    "assessment_year": account.assessment_year,
                    "assessed_value": float(account.assessed_value) if account.assessed_value else None,
                    "tax_amount": float(account.tax_amount) if account.tax_amount else None,
                    "tax_status": account.tax_status,
                    "created_at": account.created_at.isoformat() if account.created_at else None,
                    "updated_at": account.updated_at.isoformat() if account.updated_at else None
                }
                account_list.append(account_dict)
            
            return jsonify({
                "status": "success",
                "total": total_count,
                "accounts": account_list,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total_count
                }
            })
        except Exception as e:
            logger.error(f"Error fetching accounts: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch accounts: {str(e)}"
            }), 500

@app.route('/api/imported-data/accounts/<account_id>', methods=['GET'])
def get_imported_account(account_id):
    """Get details for a specific account."""
    with app.app_context():
        try:
            # Get the account
            account = Account.query.filter_by(account_id=account_id).first()
            
            if not account:
                return jsonify({
                    "status": "error",
                    "message": f"Account not found: {account_id}"
                }), 404
            
            # Convert to dictionary
            account_dict = {
                "id": account.id,
                "account_id": account.account_id,
                "owner_name": account.owner_name,
                "property_address": account.property_address,
                "property_city": account.property_city,
                "mailing_address": account.mailing_address,
                "mailing_city": account.mailing_city,
                "mailing_state": account.mailing_state,
                "mailing_zip": account.mailing_zip,
                "legal_description": account.legal_description,
                "assessment_year": account.assessment_year,
                "assessed_value": float(account.assessed_value) if account.assessed_value else None,
                "tax_amount": float(account.tax_amount) if account.tax_amount else None,
                "tax_status": account.tax_status,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None
            }
            
            return jsonify({
                "status": "success",
                "account": account_dict
            })
        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch account: {str(e)}"
            }), 500

@app.route('/api/imported-data/property-images', methods=['GET'])
def get_imported_property_images():
    """Get a list of imported property images."""
    with app.app_context():
        try:
            # Get query parameters
            offset = request.args.get('offset', 0, type=int)
            limit = request.args.get('limit', 100, type=int)
            property_id = request.args.get('property_id', '')
            image_type = request.args.get('image_type', '')
            
            # Build query
            query = PropertyImage.query
            
            # Apply filters
            if property_id:
                query = query.filter(PropertyImage.property_id.ilike(f"%{property_id}%"))
            if image_type:
                query = query.filter(PropertyImage.image_type.ilike(f"%{image_type}%"))
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            images = query.offset(offset).limit(limit).all()
            
            # Convert to dictionary
            image_list = []
            for image in images:
                image_dict = {
                    "id": image.id,
                    "property_id": image.property_id,
                    "account_id": image.account_id,
                    "image_url": image.image_url,
                    "image_path": image.image_path,
                    "image_type": image.image_type,
                    "image_date": image.image_date.isoformat() if image.image_date else None,
                    "width": image.width,
                    "height": image.height,
                    "file_size": image.file_size,
                    "file_format": image.file_format,
                    "created_at": image.created_at.isoformat() if image.created_at else None,
                    "updated_at": image.updated_at.isoformat() if image.updated_at else None
                }
                image_list.append(image_dict)
            
            return jsonify({
                "status": "success",
                "total": total_count,
                "images": image_list,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total_count
                }
            })
        except Exception as e:
            logger.error(f"Error fetching property images: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch property images: {str(e)}"
            }), 500

@app.route('/api/imported-data/improvements', methods=['GET'])
def get_imported_improvements():
    """Get a list of imported property improvements."""
    with app.app_context():
        try:
            # Get query parameters
            offset = request.args.get('offset', 0, type=int)
            limit = request.args.get('limit', 100, type=int)
            property_id = request.args.get('property_id', '')
            
            # Build query using Property model
            query = db.session.query(Property)
            
            # Apply filters
            if property_id:
                # Filter by matching parcel ID
                parcel = db.session.query(Parcel).filter(Parcel.parcel_id.ilike(f'%{property_id}%')).first()
                if parcel:
                    query = query.filter(Property.parcel_id == parcel.id)
                else:
                    # No matching parcel, return empty result
                    return jsonify({
                        'status': 'success',
                        'total': 0,
                        'improvements': [],
                        'pagination': {
                            'offset': offset,
                            'limit': limit,
                            'total': 0
                        }
                    })
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            properties = query.order_by(Property.id).offset(offset).limit(limit).all()
            
            # Prepare improvement data from properties
            improvements = []
            for prop in properties:
                # Get associated parcel for property value
                parcel = db.session.query(Parcel).filter(Parcel.id == prop.parcel_id).first()
                if parcel:
                    improvement = {
                        'id': prop.id,
                        'property_id': parcel.parcel_id if parcel else None,
                        'improvement_id': f"I-{prop.id}",  # Generate an improvement ID
                        'description': f"{prop.property_type} structure",
                        'improvement_value': float(parcel.improvement_value) if parcel and parcel.improvement_value else 0,
                        'living_area': prop.square_footage,
                        'stories': prop.stories,
                        'year_built': prop.year_built,
                        'primary_use': prop.property_type,
                        'created_at': prop.created_at.isoformat() if prop.created_at else None,
                        'updated_at': prop.updated_at.isoformat() if prop.updated_at else None
                    }
                    improvements.append(improvement)
            
            return jsonify({
                "status": "success",
                "total": total_count,
                "improvements": improvements,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total_count
                }
            })
        except Exception as e:
            logger.error(f"Error fetching improvements: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch improvements: {str(e)}"
            }), 500

@app.route('/api/discover-schema', methods=['GET'])
def discover_schema():
    """
    Discover database schema with enhanced metadata.
    
    This endpoint provides detailed schema information for database tables,
    including relationships, table statistics, and sample data.
    """
    with app.app_context():
        try:
            # Get query parameters
            db_type = request.args.get('db', 'postgres')
            include_samples = request.args.get('include_samples', 'false').lower() == 'true'
            format_for_nl = request.args.get('format_for_nl', 'false').lower() == 'true'
            
            # Import our enhanced schema discovery module
            from app.schema_discovery import get_schema_discovery_instance
            
            # Get schema discovery instance
            schema_discovery = get_schema_discovery_instance(db.engine)
            
            # If format for natural language is requested, return a formatted string
            if format_for_nl:
                schema_nl_format = schema_discovery.get_schema_for_nl()
                return jsonify({
                    "status": "success",
                    "schema_text": schema_nl_format
                })
            
            # Get all tables or focus on specific ones if specified
            tables_param = request.args.get('tables')
            if tables_param:
                tables = tables_param.split(',')
            else:
                # Default focus tables
                tables = schema_discovery.get_all_tables()
            
            # Get detailed table information
            table_details = {}
            schema_items = []
            
            for table_name in tables:
                try:
                    # Get table details
                    table_info = schema_discovery.get_table_details(table_name)
                    table_details[table_name] = table_info
                    
                    # Convert to flat schema items (backward compatibility)
                    for column in table_info.get('columns', []):
                        col_name = column.get('name')
                        is_pk = col_name in table_info.get('primary_keys', [])
                        
                        # Look for foreign keys
                        fk_info = None
                        for fk in table_info.get('foreign_keys', []):
                            if col_name in fk.get('constrained_columns', []):
                                fk_info = fk
                                break
                        
                        is_fk = fk_info is not None
                        
                        schema_item = {
                            'table_name': table_name,
                            'column_name': col_name,
                            'data_type': column.get('type'),
                            'is_nullable': column.get('nullable', True),
                            'column_default': column.get('default'),
                            'is_primary_key': is_pk,
                            'is_foreign_key': is_fk,
                            'references_table': fk_info.get('referred_table') if fk_info else None,
                            'references_column': fk_info.get('referred_columns')[0] if fk_info and fk_info.get('referred_columns') else None,
                            'description': column.get('comment', '')
                        }
                        
                        schema_items.append(schema_item)
                except Exception as e:
                    logger.warning(f"Error getting schema for table {table_name}: {str(e)}")
            
            # Get table relationships
            relationships = schema_discovery.get_table_relationships()
            
            # Get sample data if requested
            samples = {}
            if include_samples:
                for table_name in tables:
                    try:
                        samples[table_name] = schema_discovery.get_column_data_samples(table_name)
                    except Exception as e:
                        logger.warning(f"Error getting sample data for table {table_name}: {str(e)}")
            
            # Get database summary
            summary = schema_discovery.get_database_summary()
            
            # Return comprehensive schema information
            response = {
                "status": "success",
                "db_schema": schema_items,  # Backward compatibility
                "tables": list(table_details.values()),
                "relationships": relationships,
                "summary": summary
            }
            
            # Add samples if included
            if include_samples:
                response["samples"] = samples
                
            return jsonify(response)
        except Exception as e:
            logger.error(f"Error discovering schema: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to discover schema: {str(e)}"
            }), 500


@app.route('/api/export/accounts/<format>', methods=['GET'])
def export_accounts_endpoint(format):
    """Export accounts data in the specified format with filtering."""
    try:
        from export_data import export_accounts
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Cap at 5000
        return export_accounts(format=format, limit=limit)
    except Exception as e:
        logger.error(f"Error exporting accounts: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/export/improvements/<format>', methods=['GET'])
def export_improvements_endpoint(format):
    """Export improvements data in the specified format with filtering."""
    try:
        from export_data import export_improvements
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Cap at 5000
        return export_improvements(format=format, limit=limit)
    except Exception as e:
        logger.error(f"Error exporting improvements: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/export/property-images/<format>', methods=['GET'])
def export_property_images_endpoint(format):
    """Export property images data in the specified format with filtering."""
    try:
        from export_data import export_property_images
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Cap at 5000
        return export_property_images(format=format, limit=limit)
    except Exception as e:
        logger.error(f"Error exporting property images: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/export/combined/<format>', methods=['GET'])
def export_combined_data_endpoint(format):
    """Export combined data from multiple tables with filtering."""
    try:
        from export_data import export_combined_data
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Cap at 5000
        return export_combined_data(format=format, limit=limit)
    except Exception as e:
        logger.error(f"Error exporting combined data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    """
    Get data for visualization charts with filtering and aggregation.
    
    Query parameters:
    - dataset: The dataset to use (accounts, improvements, property_images, combined)
    - chart_type: Type of chart (bar, line, pie, scatter, doughnut, radar, polarArea)
    - dimension: The dimension to group by
    - measure: The measure to aggregate
    - aggregation: How to aggregate (count, sum, avg, min, max)
    - limit: Maximum number of data points (default: 25)
    - filters: JSON encoded filters to apply
    """
    try:
        # Get query parameters
        dataset = request.args.get('dataset', 'accounts')
        chart_type = request.args.get('chart_type', 'bar')
        dimension = request.args.get('dimension', None)
        measure = request.args.get('measure', None)
        aggregation = request.args.get('aggregation', 'count')
        limit = min(int(request.args.get('limit', 25)), 50)  # Cap at 50 data points
        
        # Handle filters if provided
        filters = {}
        try:
            import json
            filters_param = request.args.get('filters', '{}')
            if filters_param:
                filters = json.loads(filters_param)
        except json.JSONDecodeError:
            logger.warning(f"Invalid filters JSON: {request.args.get('filters')}")
            
        logger.info(f"Chart request: dataset={dataset}, dimension={dimension}, measure={measure}, agg={aggregation}")
        
        # Choose the right model based on dataset
        if dataset == 'accounts':
            model = Account
            default_dimension = 'owner_name'  # Changed from property_city since that field is empty
            default_measure = 'id'  # Changed from assessed_value since that field is empty
        elif dataset == 'improvements':
            from sqlalchemy import text
            default_dimension = 'IMPR_CODE'
            default_measure = 'IMPR_VALUE'
        elif dataset == 'property_images':
            model = PropertyImage
            default_dimension = 'image_type'
            default_measure = 'id'
        else:
            # Default to accounts
            model = Account
            default_dimension = 'owner_name'  # Changed from property_city
            default_measure = 'id'  # Changed from assessed_value
            
        # Use defaults if not specified
        dimension = dimension or default_dimension
        measure = measure or default_measure
            
        # Start building the query based on the model
        with app.app_context():
            if dataset == 'improvements':
                # Handle improvements table separately with raw SQL
                # Use Property model instead since we don't have a direct improvements model
                property_query = db.session.query(
                    Property.property_type.label('dimension'),
                    func.count(Property.id).label('value')
                )
                
                # Apply filters if any
                if filters:
                    for key, value in filters.items():
                        if hasattr(Property, key):
                            property_query = property_query.filter(getattr(Property, key) == value)
                
                # Group by dimension and order by count
                property_query = property_query.group_by(Property.property_type)
                property_query = property_query.order_by(func.count(Property.id).desc())
                property_query = property_query.limit(limit)
                
                # Execute the query
                result = property_query.all()
                data = [{'dimension': row.dimension, 'value': float(row.value)} for row in result]
                
            else:
                # Handle standard SQLAlchemy models
                from sqlalchemy import func, case, cast, Float
                
                # Define the aggregation function
                if aggregation == 'count':
                    agg_value = func.count(getattr(model, measure))
                elif aggregation == 'sum':
                    agg_value = func.sum(cast(getattr(model, measure), Float))
                elif aggregation == 'avg':
                    agg_value = func.avg(cast(getattr(model, measure), Float))
                elif aggregation == 'min':
                    agg_value = func.min(cast(getattr(model, measure), Float))
                elif aggregation == 'max':
                    agg_value = func.max(cast(getattr(model, measure), Float))
                else:
                    agg_value = func.count(getattr(model, measure))
                
                # Start building the query
                query = db.session.query(
                    getattr(model, dimension).label('dimension'),
                    agg_value.label('value')
                )
                
                # Apply filters
                for key, value in filters.items():
                    if hasattr(model, key):
                        query = query.filter(getattr(model, key) == value)
                
                # Apply aggregation
                query = query.group_by(getattr(model, dimension))
                
                # Sort by the aggregated value in descending order
                query = query.order_by(agg_value.desc())
                
                # Apply limit
                query = query.limit(limit)
                
                # Execute the query and convert to list of dictionaries
                data = [
                    {'dimension': row.dimension, 'value': float(row.value) if row.value is not None else 0}
                    for row in query.all()
                ]
            
            # Return chart data with appropriate metadata
            return jsonify({
                "status": "success",
                "chart_data": {
                    "dataset": dataset,
                    "chart_type": chart_type,
                    "dimension": dimension,
                    "measure": measure,
                    "aggregation": aggregation,
                    "data": data
                }
            })
            
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to generate chart data: {str(e)}"
        }), 500


@app.route('/api/query', methods=['POST'])
def run_query():
    """
    Execute a SQL query against the database.
    
    Request JSON body:
    {
        "db": "postgres",  // Database to query
        "query": "SELECT * FROM accounts LIMIT 10",  // SQL query to execute
        "params": [],  // Optional list or dict of parameters
        "param_style": "format",  // Optional parameter style
        "page": 1,  // Optional page number for pagination
        "page_size": 50,  // Optional page size for pagination
        "security_level": "medium"  // Optional security validation level
    }
    
    Returns:
    {
        "status": "success",
        "data": [...],  // Query results
        "execution_time": 0.123,  // Execution time in seconds
        "pagination": {  // Pagination metadata if page_size is specified
            "page": 1,
            "page_size": 50,
            "total_records": 1000,
            "total_pages": 20,
            "has_next": true,
            "has_prev": false
        }
    }
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
        
        # Extract query parameters
        db = data.get('db', 'postgres')
        query = data.get('query')
        params = data.get('params')
        param_style = data.get('param_style', 'format')
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        security_level = data.get('security_level', 'medium')
        
        # Validate query is provided
        if not query:
            return jsonify({
                "status": "error",
                "message": "No SQL query provided"
            }), 400
        
        # Log the query
        logger.info(f"Executing query: {query[:100]}...")
        
        # If no params provided, try to extract them from the query
        if params is None:
            parsed_query, extracted_params = parse_for_parameters(query)
            # Use the parsed query and extracted params if any were found
            if extracted_params:
                query = parsed_query
                params = extracted_params
                logger.info(f"Extracted {len(params)} parameters from query: {params}")
        
        # Execute the query
        result = execute_parameterized_query(
            db=db,
            query=query,
            params=params,
            param_style=param_style,
            page=page,
            page_size=page_size,
            security_level=security_level
        )
        
        # Return the result
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Query execution failed: {str(e)}"
        }), 500


@app.route('/api/chart-metadata', methods=['GET'])
def get_chart_metadata():
    """
    Get available chart dimensions and measures for each dataset.
    This endpoint provides metadata needed by the enhanced chart builder.
    
    Returns:
    {
        "status": "success",
        "metadata": {
            "accounts": {
                "dimensions": [...],
                "measures": [...]
            },
            "property_images": {
                "dimensions": [...],
                "measures": [...]
            },
            ...
        }
    }
    """
    try:
        # Define field mappings for each dataset
        metadata = {
            "accounts": {
                "dimensions": [
                    {"value": "owner_name", "label": "Owner Name"},
                    {"value": "assessment_year", "label": "Assessment Year"},
                    {"value": "tax_status", "label": "Tax Status"},
                    {"value": "mailing_city", "label": "Mailing City"},
                    {"value": "mailing_state", "label": "Mailing State"},
                    {"value": "mailing_zip", "label": "Mailing ZIP"}
                ],
                "measures": [
                    {"value": "id", "label": "Count"},
                    {"value": "assessed_value", "label": "Assessed Value"},
                    {"value": "tax_amount", "label": "Tax Amount"}
                ]
            },
            "property_images": {
                "dimensions": [
                    {"value": "image_type", "label": "Image Type"},
                    {"value": "file_format", "label": "File Format"},
                    {"value": "EXTRACT(YEAR FROM image_date)", "label": "Image Year"}
                ],
                "measures": [
                    {"value": "file_size", "label": "File Size"},
                    {"value": "width", "label": "Width"},
                    {"value": "height", "label": "Height"},
                    {"value": "id", "label": "Count"}
                ]
            },
            "improvements": {
                "dimensions": [
                    {"value": "IMPR_CODE", "label": "Improvement Code"},
                    {"value": "YEAR_BUILT", "label": "Year Built"},
                    {"value": "FLOOR(LIVING_AREA / 500) * 500", "label": "Living Area Range"}
                ],
                "measures": [
                    {"value": "IMPR_VALUE", "label": "Improvement Value"},
                    {"value": "LIVING_AREA", "label": "Living Area"},
                    {"value": "NUM_STORIES", "label": "Number of Stories"},
                    {"value": "id", "label": "Count"}
                ]
            }
        }
        
        # Get list of available image types, improvement codes, etc.
        with app.app_context():
            # Get distinct image types
            image_types = db.session.query(PropertyImage.image_type).distinct().all()
            metadata["available_filters"] = {
                "image_types": [t[0] for t in image_types if t[0]],
                "years": list(range(2010, 2026))
            }
        
        return jsonify({
            "status": "success",
            "metadata": metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting chart metadata: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve chart metadata: {str(e)}"
        }), 500


@app.route('/api/nl-to-sql', methods=['POST'])
def nl_to_sql():
    """
    Convert natural language query to SQL.
    
    Request JSON body:
    {
        "query": "Find all accounts with property in Richland",
        "db": "postgres"
    }
    
    Returns:
    {
        "status": "success",
        "sql": "SELECT * FROM accounts WHERE property_city = 'Richland'",
        "explanation": "This query retrieves all account records where the property city is 'Richland'."
    }
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
        
        # Extract query parameters
        nl_query = data.get('query')
        db_type = data.get('db', 'postgres')
        
        # Validate query is provided
        if not nl_query:
            return jsonify({
                "status": "error",
                "message": "No natural language query provided"
            }), 400
        
        # Log the query
        logger.info(f"Processing natural language query: {nl_query}")
        
        # Use our nl_to_sql implementation from app.nl_processing
        from app.nl_processing import nl_to_sql as process_nl_to_sql
        
        # Process the query using our dedicated module
        result = process_nl_to_sql(nl_query, db_type)
        
        # Return the result
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing natural language query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Natural language processing failed: {str(e)}"
        }), 500


@app.route('/api/parameterized-query', methods=['POST'])
def parameterized_query():
    """
    Execute a parameterized SQL query with named parameters.
    
    Request JSON body:
    {
        "db": "postgres",
        "query": "SELECT * FROM accounts WHERE account_id = :account_id",
        "params": {
            "account_id": "123456"
        },
        "param_style": "named",
        "page": 1,
        "page_size": 50
    }
    
    Returns same structure as /api/query endpoint.
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
        
        # Extract query parameters
        db = data.get('db', 'postgres')
        query = data.get('query')
        params = data.get('params')
        param_style = data.get('param_style', 'named')
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        security_level = data.get('security_level', 'medium')
        
        # Validate query is provided
        if not query:
            return jsonify({
                "status": "error",
                "message": "No SQL query provided"
            }), 400
        
        # Validate params is provided
        if params is None:
            return jsonify({
                "status": "error",
                "message": "No parameters provided for parameterized query"
            }), 400
        
        # Log the query
        logger.info(f"Executing parameterized query: {query[:100]}...")
        
        # Execute the query
        result = execute_parameterized_query(
            db=db,
            query=query,
            params=params,
            param_style=param_style,
            page=page,
            page_size=page_size,
            security_level=security_level
        )
        
        # Return the result
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error executing parameterized query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Parameterized query execution failed: {str(e)}"
        }), 500


@app.route('/')
def index():
    """Handle the root route."""
    return render_template('index_minimal.html', title="Benton County Assessor")


@app.route('/query-builder')
def query_builder():
    """Render the query builder interface."""
    return render_template('query_builder.html', title="SQL Query Builder")


@app.route('/nl-query')
def nl_query():
    """Render the natural language query interface."""
    return render_template('nl_query.html', title="Natural Language Query")

@app.route('/api/nl-query-debug', methods=['POST'])
def nl_query_debug():
    """
    Debug endpoint for natural language query intent extraction.
    This endpoint shows the interpreted intent from a natural language query
    without executing the SQL, useful for testing and debugging.
    
    Request JSON body:
    {
        "query": "Show me all properties in Richland worth more than 200000"
    }
    
    Returns:
    {
        "status": "success",
        "query": "original query text",
        "intent": {
            "action": "retrieve",
            "table": "accounts",
            "fields": ["*"],
            "conditions": [...],
            ...
        }
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: query"
            }), 400
        
        nl_query_text = data['query']
        
        # Extract intent from natural language query
        from app.nl_processing import extract_query_intent
        intent = extract_query_intent(nl_query_text)
        
        return jsonify({
            "status": "success",
            "query": nl_query_text,
            "intent": intent
        })
    
    except Exception as e:
        logger.error(f"Error processing natural language query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process natural language query: {str(e)}"
        }), 500


@app.route('/visualize')
def visualize():
    """Render the data visualization interface."""
    # Get unique values for dropdown filters
    with app.app_context():
        try:
            # Get cities (using mailing_city since property_city is often empty)
            cities_query = db.session.query(Account.mailing_city)\
                .filter(Account.mailing_city != None, Account.mailing_city != '')\
                .distinct()\
                .order_by(Account.mailing_city)
            cities = [city[0] for city in cities_query.all()]
        except Exception as e:
            logger.error(f"Error fetching cities: {str(e)}")
            cities = []
        
        try:
            # Get property types
            property_types_query = db.session.query(Property.property_type)\
                .filter(Property.property_type != None, Property.property_type != '')\
                .distinct()\
                .order_by(Property.property_type)
            property_types = [p_type[0] for p_type in property_types_query.all()]
        except Exception as e:
            logger.error(f"Error fetching property types: {str(e)}")
            property_types = []
        
        try:
            # Get image types for filtering
            image_types_query = db.session.query(PropertyImage.image_type)\
                .filter(PropertyImage.image_type != None, PropertyImage.image_type != '')\
                .distinct()\
                .order_by(PropertyImage.image_type)
            image_types = [i_type[0] for i_type in image_types_query.all()]
        except Exception as e:
            logger.error(f"Error fetching image types: {str(e)}")
            image_types = []
        
        try:
            # Get improvement codes
            improvement_codes_query = db.session.query(text("DISTINCT impr_code FROM ftp_dl_imprv"))\
                .filter(text("impr_code IS NOT NULL"))\
                .order_by(text("impr_code"))
            improvement_codes = [code[0] for code in db.session.execute(improvement_codes_query)]
        except Exception as e:
            logger.error(f"Error fetching improvement codes: {str(e)}")
            improvement_codes = []
        
    # Get current year and previous year for statistics
    current_year = datetime.datetime.now().year
    previous_year = current_year - 1
    
    return render_template(
        'visualize.html', 
        title="MCP Assessor Data Visualization",
        version="2.0",
        cities=cities,
        property_types=property_types,
        image_types=image_types,
        improvement_codes=improvement_codes,
        current_year=current_year,
        previous_year=previous_year
    )


@app.route('/map-view')
def map_view():
    """Render the property map view interface with enhanced visualization."""
    return render_template('map_view_minimal.html', title="Enhanced Property Map")
    
# Map API endpoints
@app.route('/api/map/data', methods=['GET'])
def map_data():
    """Get map data with advanced filtering and visualization options."""
    # Enhanced implementation uses query parameters directly from the request
    return map_module.get_map_data(limit=1000, use_cache=True)

@app.route('/api/map/cities', methods=['GET'])
def map_cities():
    """Get list of cities for map filtering."""
    return map_module.get_cities()

@app.route('/api/map/property-types', methods=['GET'])
def map_property_types():
    """Get list of property types for map filtering."""
    return map_module.get_property_types()

@app.route('/api/map/value-ranges', methods=['GET'])
def map_value_ranges():
    """Get property value ranges for filtering."""
    return map_module.get_value_ranges()

@app.route('/api/map/property-images/<account_id>', methods=['GET'])
def map_property_images(account_id):
    """Get property images for a specific account."""
    # Pass the account_id to the map module function
    return map_module.get_property_images_for_map(account_id)

@app.route('/api/map/clear-cache', methods=['POST'])
def map_clear_cache():
    """Clear the map data cache."""
    map_module.clear_cache()
    return jsonify({"status": "success", "message": "Map cache cleared successfully"})


# Global variable to store the agent coordinator instance
agent_coordinator = None
agent_list = []

# Initialize agent-assisted development framework
def initialize_agent_framework():
    """Initialize the agent-assisted development framework."""
    global agent_coordinator, agent_list
    
    try:
        # Try to import the agent integration module
        from agent_coordination.integration import initialize_agent_development_system
        
        logger.info("Initializing agent-assisted development framework...")
        
        # Initialize the framework (without a real hub for now)
        coordinator, agents = initialize_agent_development_system()
        
        if coordinator:
            logger.info(f"Agent coordinator initialized successfully")
            if agents:
                logger.info(f"Initialized {len(agents)} development agents")
                for agent in agents:
                    logger.info(f"  - Agent '{agent.agent_id}' ready")
            else:
                logger.info("No development agents were initialized")
            
            # Store in global variables
            agent_coordinator = coordinator
            agent_list = agents
            
            return coordinator, agents
            
    except ImportError as e:
        logger.warning(f"Agent-assisted development framework not available: {e}")
    except Exception as e:
        logger.error(f"Error initializing agent framework: {str(e)}")
        
    # If import failed or no coordinator was created, create a simple mock coordinator
    try:
        # Set up a basic mock coordinator if import fails
        logger.info("Creating mock agent coordinator")
        
        # Define a minimal MockAgent class
        class MockAgent:
            def __init__(self, agent_id, agent_type, capabilities):
                self.agent_id = agent_id
                self.agent_type = agent_type
                self.capabilities = capabilities
                
        # Define a minimal mock coordinator with the needed API functions
        class MockCoordinator:
            def __init__(self):
                self.tasks = {}
                self.current_id = 0
                logger.info("Mock coordinator initialized")
                
            def create_task(self, task_data):
                self.current_id += 1
                task_id = f"task-{self.current_id}"
                self.tasks[task_id] = self._create_task_obj(task_id, task_data)
                logger.info(f"Created mock task {task_id}")
                return task_id
                
            def assign_task(self, task_id, agent_id=None):
                if task_id in self.tasks:
                    if agent_id:
                        self.tasks[task_id]["agent_id"] = agent_id
                    else:
                        self.tasks[task_id]["agent_id"] = "python_developer"
                    self.tasks[task_id]["status"] = "assigned"
                    logger.info(f"Assigned mock task {task_id} to agent {self.tasks[task_id]['agent_id']}")
                    return True
                return False
                
            def get_tasks_by_status(self, status):
                return [task for task_id, task in self.tasks.items() if task.get("status") == status]
                
            def analyze_codebase(self):
                logger.info("Analyzing codebase (mock)")
                return {
                    "modules": [{"name": "main.py"}, {"name": "models.py"}],
                    "code_quality": {"issues": []},
                    "test_coverage": {"low_coverage": []}
                }
                
            def generate_tasks_from_analysis(self, analysis):
                logger.info("Generating tasks from analysis (mock)")
                task_id = self.create_task({
                    "title": "Improve test coverage",
                    "description": "Create tests for modules with low coverage",
                    "task_type": "testing",
                    "priority": "medium"
                })
                return [task_id]
                
            def _create_task_obj(self, task_id, data):
                from datetime import datetime
                return {
                    "task_id": task_id,
                    "title": data.get("title", "Untitled Task"),
                    "description": data.get("description", ""),
                    "task_type": data.get("task_type", ""),
                    "priority": data.get("priority", "medium"),
                    "status": "pending",
                    "agent_id": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
        # Create mock coordinator and agents
        mock_coordinator = MockCoordinator()
        mock_agents = [
            MockAgent("python_developer", "developer", ["code_generation", "code_review", "testing", "documentation"]),
            MockAgent("web_developer", "developer", ["ui_design", "frontend_development", "css_styling"]),
            MockAgent("data_validator", "validator", ["data_validation", "anomaly_detection", "quality_reporting"])
        ]
        
        # Store in global variables
        agent_coordinator = mock_coordinator
        agent_list = mock_agents
        
        logger.info(f"Initialized mock framework with {len(mock_agents)} agents")
        return mock_coordinator, mock_agents
        
    except Exception as e:
        logger.error(f"Error creating mock coordinator: {str(e)}")
        return None, []

# API endpoints for agent-assisted development
@app.route('/api/dev/tasks', methods=['GET'])
def get_development_tasks():
    """Get all development tasks."""
    global agent_coordinator
    
    if agent_coordinator is None:
        return jsonify({
            "status": "error",
            "message": "Agent coordinator not initialized"
        }), 500
    
    try:
        # Get task data
        tasks = {}
        
        # Check if we're using a real coordinator (with get_tasks_by_status returning task objects)
        # or mock coordinator (where tasks are plain dictionaries)
        for status in ["pending", "assigned", "in_progress", "completed", "failed"]:
            status_tasks = agent_coordinator.get_tasks_by_status(status)
            
            if not status_tasks:
                continue
                
            # Check if we got task objects or plain dictionaries
            if hasattr(status_tasks[0], 'task_id'):
                # Real task objects
                for task in status_tasks:
                    tasks[task.task_id] = {
                        "task_id": task.task_id,
                        "title": task.title,
                        "description": task.description,
                        "task_type": task.task_type,
                        "priority": task.priority,
                        "status": task.status,
                        "agent_id": task.agent_id,
                        "created_at": task.created_at,
                        "updated_at": task.updated_at
                    }
            else:
                # Mock tasks (dictionaries)
                for task in status_tasks:
                    task_id = task.get("task_id", "unknown")
                    tasks[task_id] = task
        
        # If we're using the mock coordinator with tasks as a dict
        if hasattr(agent_coordinator, "tasks") and isinstance(agent_coordinator.tasks, dict):
            # Add all tasks from the tasks dictionary
            for task_id, task in agent_coordinator.tasks.items():
                if task_id not in tasks:
                    tasks[task_id] = task
        
        return jsonify({
            "status": "success",
            "tasks": tasks
        })
    except Exception as e:
        logger.error(f"Error fetching development tasks: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch development tasks: {str(e)}"
        }), 500

@app.route('/api/dev/tasks', methods=['POST'])
def create_development_task():
    """Create a new development task."""
    global agent_coordinator
    
    if agent_coordinator is None:
        return jsonify({
            "status": "error",
            "message": "Agent coordinator not initialized"
        }), 500
    
    try:
        # Get task data from request
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No task data provided"
            }), 400
        
        # Create task
        task_id = agent_coordinator.create_task(data)
        
        # Auto-assign if requested
        auto_assign = data.get("auto_assign", False)
        if auto_assign:
            agent_coordinator.assign_task(task_id)
            
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "message": "Task created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating development task: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to create development task: {str(e)}"
        }), 500

@app.route('/api/dev/tasks/<task_id>/assign', methods=['POST'])
def assign_development_task(task_id):
    """Assign a development task to an agent."""
    global agent_coordinator
    
    if agent_coordinator is None:
        return jsonify({
            "status": "error",
            "message": "Agent coordinator not initialized"
        }), 500
    
    try:
        # Get agent ID from request
        data = request.json or {}
        agent_id = data.get("agent_id")
        
        # Assign task
        success = agent_coordinator.assign_task(task_id, agent_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Task {task_id} assigned successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to assign task {task_id}"
            }), 400
    except Exception as e:
        logger.error(f"Error assigning development task: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to assign development task: {str(e)}"
        }), 500

@app.route('/api/dev/agents', methods=['GET'])
def get_development_agents():
    """Get all development agents."""
    global agent_list
    
    try:
        # Get agent data
        agents = []
        for agent in agent_list:
            agents.append({
                "agent_id": agent.agent_id,
                "agent_type": getattr(agent, "agent_type", "unknown"),
                "capabilities": getattr(agent, "capabilities", []),
                "specialization": getattr(agent, "specialization", "unknown")
            })
        
        return jsonify({
            "status": "success",
            "agents": agents
        })
    except Exception as e:
        logger.error(f"Error fetching development agents: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch development agents: {str(e)}"
        }), 500

@app.route('/api/dev/analyze', methods=['POST'])
def analyze_codebase():
    """Analyze the codebase and generate tasks."""
    global agent_coordinator
    
    if agent_coordinator is None:
        return jsonify({
            "status": "error",
            "message": "Agent coordinator not initialized"
        }), 500
    
    try:
        # Analyze codebase
        analysis = agent_coordinator.analyze_codebase()
        
        # Generate tasks from analysis if requested
        generate_tasks = request.json.get("generate_tasks", False) if request.json else False
        task_ids = []
        
        if generate_tasks:
            task_ids = agent_coordinator.generate_tasks_from_analysis(analysis)
        
        return jsonify({
            "status": "success",
            "analysis": {
                "modules_count": len(analysis.get("modules", [])),
                "code_quality": {
                    "issue_count": len(analysis.get("code_quality", {}).get("issues", []))
                },
                "test_coverage": {
                    "low_coverage_count": len(analysis.get("test_coverage", {}).get("low_coverage", []))
                }
            },
            "tasks_generated": len(task_ids),
            "task_ids": task_ids
        })
    except Exception as e:
        logger.error(f"Error analyzing codebase: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to analyze codebase: {str(e)}"
        }), 500

# Initialize the agent coordinator on app start
with app.app_context():
    # Initialize agent-assisted development framework
    logger.info("Initializing agent coordination framework during app startup...")
    coordinator, agents = initialize_agent_framework()
    
    if coordinator:
        logger.info(f"Agent coordination framework initialized with {len(agents)} agents")
        # Create a sample task to ensure everything is working
        try:
            task_id = coordinator.create_task({
                "title": "Sample Development Task",
                "description": "This is a sample task created during server startup to verify the agent coordination framework.",
                "task_type": "documentation",
                "priority": "low"
            })
            logger.info(f"Created sample task {task_id} during startup")
        except Exception as e:
            logger.error(f"Error creating sample task: {str(e)}")
    else:
        logger.error("Failed to initialize agent coordination framework")


# This is called when the Flask app is run
if __name__ == "__main__":
    # Register authentication demo routes
    try:
        from app.auth.demo_routes import register_auth_demo_routes
        register_auth_demo_routes(app)
        logger.info("Authentication demo routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register authentication demo routes: {e}")
    
    # Create tables and seed database if needed
    create_tables()
    seed_database_if_needed()
    
    try:
        # Log that we're starting the Flask app
        logger.info("Starting MCP Assessor Agent API server (Flask only)...")
        
        # Run the Flask app
        app.run(host="0.0.0.0", port=FLASK_PORT, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        cleanup_on_exit()