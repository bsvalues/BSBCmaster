"""
This file provides a combined server for both Flask documentation and backend services.
It serves as the main entry point for the application in Replit.
"""

import os
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
import map_module

from app_setup import app, db, create_tables
from routes import api_routes
from models import Parcel, Property, Sale, Account, PropertyImage
from app.db import execute_parameterized_query, parse_for_parameters, sql_to_natural_language, get_connection_string
from sqlalchemy import create_engine, inspect
from app.validators import validate_query
import map_module

# Register routes
app.register_blueprint(api_routes)

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
            "app:app", 
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
    """Discover database schema."""
    with app.app_context():
        try:
            # Get query parameters
            db_type = request.args.get('db', 'postgres')
            
            # We'll focus on the main tables
            tables = ['parcels', 'properties', 'sales', 'accounts', 'property_images', 'improvements']
            
            # Get schema information from SQLAlchemy metadata
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            schema_items = []
            
            for table_name in tables:
                try:
                    columns = inspector.get_columns(table_name)
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    primary_keys = pk_constraint.get('constrained_columns', [])
                    
                    # Get foreign keys
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    fk_columns = {}
                    for fk in foreign_keys:
                        for col in fk.get('constrained_columns', []):
                            fk_columns[col] = {
                                'table': fk.get('referred_table'),
                                'column': fk.get('referred_columns')[0] if fk.get('referred_columns') else None
                            }
                    
                    # Add each column to the schema
                    for column in columns:
                        col_name = column.get('name')
                        is_pk = col_name in primary_keys
                        is_fk = col_name in fk_columns
                        
                        schema_item = {
                            'table_name': table_name,
                            'column_name': col_name,
                            'data_type': str(column.get('type')),
                            'is_nullable': column.get('nullable', True),
                            'column_default': str(column.get('default')) if column.get('default') else None,
                            'is_primary_key': is_pk,
                            'is_foreign_key': is_fk,
                            'references_table': fk_columns.get(col_name, {}).get('table') if is_fk else None,
                            'references_column': fk_columns.get(col_name, {}).get('column') if is_fk else None,
                            'description': None  # We don't have descriptions in our schema
                        }
                        
                        schema_items.append(schema_item)
                except Exception as e:
                    logger.warning(f"Error getting schema for table {table_name}: {str(e)}")
            
            return jsonify({
                "status": "success",
                "db_schema": schema_items
            })
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
        
        # Try to use OpenAI if available
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if openai_api_key:
            try:
                import openai
                openai.api_key = openai_api_key
                
                # Get database schema information for context
                schema_info = ""
                
                # We'll use a simplified schema for context as we can't access the whole schema dynamically
                schema_info = """
                Tables:
                - accounts (account_id, owner_name, property_address, property_city, mailing_address, mailing_city, mailing_state, mailing_zip, legal_description, assessment_year, assessed_value, tax_amount, tax_status)
                - property_images (id, property_id, account_id, image_url, image_path, image_type, image_date, width, height, file_size, file_format)
                - properties (id, parcel_id, property_type, square_footage, bedrooms, bathrooms, year_built, stories)
                - parcels (id, parcel_id, land_value, improvement_value, total_value, land_use_code, zoning_code)
                - sales (id, parcel_id, sale_date, sale_price, sale_type, buyer_name, seller_name)
                """
                
                # Create a prompt for the OpenAI model
                prompt = f"""
                Convert the following natural language query to SQL for a PostgreSQL database. Return only valid SQL without explanations.
                
                The database schema is:
                {schema_info}
                
                Natural language query: {nl_query}
                
                SQL query:
                """
                
                # Call OpenAI API
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.3,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                
                # Extract the SQL from the response
                generated_sql = response.choices[0].text.strip()
                
                # Create an explanation prompt
                explanation_prompt = f"""
                Explain the following SQL query in simple, non-technical terms, one or two sentences maximum:
                
                {generated_sql}
                """
                
                # Get explanation from OpenAI
                explanation_response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=explanation_prompt,
                    max_tokens=100,
                    temperature=0.3,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                
                explanation = explanation_response.choices[0].text.strip()
                
                # Add default LIMIT if not present
                if "LIMIT" not in generated_sql.upper():
                    generated_sql += " LIMIT 100"
                
                return jsonify({
                    "status": "success",
                    "sql": generated_sql,
                    "explanation": explanation
                })
                
            except ImportError:
                logger.warning("OpenAI package not installed, falling back to rule-based conversion")
            except Exception as e:
                logger.warning(f"Error using OpenAI API: {str(e)}, falling back to rule-based conversion")
        
        # Enhanced rule-based conversion if OpenAI is not available or fails
        sql_query = ""
        explanation = ""
        
        # Keyword mapping to determine table
        table_keywords = {
            'account': 'accounts',
            'accounts': 'accounts',
            'property': 'properties',
            'properties': 'properties',
            'sale': 'sales',
            'sales': 'sales',
            'parcel': 'parcels',
            'parcels': 'parcels',
            'image': 'property_images',
            'images': 'property_images',
            'improvement': 'properties',
            'improvements': 'properties'
        }
        
        # Determine the main table from keywords
        table = 'accounts'  # Default table
        for keyword, table_name in table_keywords.items():
            if keyword.lower() in nl_query.lower():
                table = table_name
                break
        
        # Build the base query
        sql_query = f"SELECT * FROM {table}"
        explanation = f"This query retrieves records from the {table} table."
        
        # Check for aggregation functions
        if any(word in nl_query.lower() for word in ['count', 'how many']):
            sql_query = f"SELECT COUNT(*) AS count FROM {table}"
            explanation = f"This query counts the total number of records in the {table} table."
        elif any(word in nl_query.lower() for word in ['average', 'avg']):
            for col in ['assessed_value', 'land_value', 'improvement_value', 'sale_price', 'square_footage']:
                if col.replace('_', ' ') in nl_query.lower():
                    sql_query = f"SELECT AVG({col}) AS average FROM {table}"
                    explanation = f"This query calculates the average {col.replace('_', ' ')} in the {table} table."
                    break
        elif any(word in nl_query.lower() for word in ['sum', 'total']):
            for col in ['assessed_value', 'land_value', 'improvement_value', 'sale_price']:
                if col.replace('_', ' ') in nl_query.lower():
                    sql_query = f"SELECT SUM({col}) AS total FROM {table}"
                    explanation = f"This query calculates the total {col.replace('_', ' ')} in the {table} table."
                    break
        
        # Check for filter conditions
        conditions = []
        
        # Location-based filters
        location_matches = re.findall(r"(in|at|from|located in|located at) ['\"]?([\w\s]+)['\"]?", nl_query, re.IGNORECASE)
        if location_matches:
            location = location_matches[0][1]
            if table == 'accounts':
                conditions.append(f"property_city ILIKE '%{location}%'")
                explanation = f"This query finds accounts in {location}."
            elif table == 'properties':
                conditions.append(f"property_address ILIKE '%{location}%'")
                explanation = f"This query finds properties in {location}."
        
        # Owner name filters
        owner_matches = re.findall(r"(owned by|owned|owner|name is|named) ['\"]?([\w\s]+)['\"]?", nl_query, re.IGNORECASE)
        if owner_matches:
            owner = owner_matches[0][1]
            if table in ['accounts', 'parcels']:
                conditions.append(f"owner_name ILIKE '%{owner}%'")
                explanation = f"This query finds {table} owned by {owner}."
        
        # Value-based filters
        value_matches = re.findall(r"(value|worth|cost|price) (greater than|more than|over|above|less than|under|below) ['\"]?(\d+)['\"]?", nl_query, re.IGNORECASE)
        if value_matches:
            comparison = value_matches[0][1]
            value = value_matches[0][2]
            operator = '>' if any(x in comparison.lower() for x in ['greater', 'more', 'over', 'above']) else '<'
            
            # Determine appropriate value column based on table
            value_column = 'assessed_value'
            if table == 'properties':
                value_column = 'total_value'
            elif table == 'sales':
                value_column = 'sale_price'
            
            conditions.append(f"{value_column} {operator} {value}")
            explanation = f"This query finds {table} with {value_column.replace('_', ' ')} {operator} {value}."
        
        # Time-based filters
        year_matches = re.findall(r"(from|in|after|before|since|until) (year|the year) ['\"]?(\d{4})['\"]?", nl_query, re.IGNORECASE)
        if year_matches:
            comparison = year_matches[0][0].lower()
            year = year_matches[0][2]
            
            operator = '>=' if any(x in comparison for x in ['after', 'since']) else '<=' if any(x in comparison for x in ['before', 'until']) else '='
            
            # Determine appropriate date/year column based on table
            date_column = 'assessment_year'
            if table == 'properties':
                date_column = 'year_built'
            elif table == 'sales':
                date_column = 'sale_date'
                conditions.append(f"EXTRACT(YEAR FROM {date_column}) {operator} {year}")
            else:
                conditions.append(f"{date_column} {operator} {year}")
            
            explanation = f"This query finds {table} {comparison} {year}."
        
        # Add conditions to query if any
        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)
        
        # Add ordering
        if 'newest' in nl_query.lower() or 'latest' in nl_query.lower() or 'recent' in nl_query.lower():
            if table == 'sales':
                sql_query += " ORDER BY sale_date DESC"
            elif table == 'property_images':
                sql_query += " ORDER BY image_date DESC"
            elif table == 'properties':
                sql_query += " ORDER BY year_built DESC"
            else:
                sql_query += " ORDER BY id DESC"
            explanation += " Results are ordered by most recent first."
        elif 'oldest' in nl_query.lower():
            if table == 'sales':
                sql_query += " ORDER BY sale_date ASC"
            elif table == 'property_images':
                sql_query += " ORDER BY image_date ASC"
            elif table == 'properties':
                sql_query += " ORDER BY year_built ASC"
            else:
                sql_query += " ORDER BY id ASC"
            explanation += " Results are ordered by oldest first."
        elif any(word in nl_query.lower() for word in ['expensive', 'highest value', 'most valuable']):
            if table in ['accounts', 'parcels']:
                sql_query += " ORDER BY assessed_value DESC"
            elif table == 'sales':
                sql_query += " ORDER BY sale_price DESC"
            elif table == 'properties':
                sql_query += " ORDER BY total_value DESC"
            explanation += " Results are ordered by highest value first."
        
        # Add limit
        limit_matches = re.findall(r"(limit|top|first) (\d+)", nl_query, re.IGNORECASE)
        if limit_matches:
            limit = limit_matches[0][1]
            sql_query += f" LIMIT {limit}"
            explanation += f" Limited to {limit} results."
        else:
            # Add a default limit for safety
            sql_query += " LIMIT 100"
            explanation += " Limited to 100 results for performance."
        
        # Get a natural language explanation of the SQL query if possible
        try:
            nl_explanation = sql_to_natural_language(sql_query)
            if nl_explanation:
                explanation = nl_explanation
        except Exception as e:
            logger.warning(f"Error generating natural language explanation: {e}")
        
        # Return the result
        return jsonify({
            "status": "success",
            "sql": sql_query,
            "explanation": explanation
        })
        
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
    return render_template('index.html', title="MCP Assessor Agent API")


@app.route('/query-builder')
def query_builder():
    """Render the query builder interface."""
    return render_template('query_builder.html', title="SQL Query Builder")


@app.route('/nl-query')
def nl_query():
    """Render the natural language query interface."""
    return render_template('nl_query.html', title="Natural Language Query")


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
    """Render the property map view interface."""
    return render_template('map_view.html', title="Property Map")
    
# Map API endpoints
@app.route('/api/map/data', methods=['GET'])
def map_data():
    """Get map data with filtering options."""
    return map_module.get_map_data()

@app.route('/api/map/cities', methods=['GET'])
def map_cities():
    """Get list of cities for map filtering."""
    return map_module.get_cities()

@app.route('/api/map/property-images/<account_id>', methods=['GET'])
def map_property_images(account_id):
    """Get property images for a specific account."""
    return map_module.get_property_images_for_map()


# This is called when the Flask app is run
if __name__ == "__main__":
    # Create tables and seed database if needed
    create_tables()
    seed_database_if_needed()
    
    try:
        # Log that we're only running the Flask app now
        logger.info("Starting MCP Assessor Agent API server (Flask only)...")
        
        # Run the Flask app
        app.run(host="0.0.0.0", port=FLASK_PORT, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        cleanup_on_exit()