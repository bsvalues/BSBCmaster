"""
This module provides Flask routes for the MCP Assessor Agent API.
"""

import os
import logging
import requests
import datetime
from flask import render_template, jsonify, request, Blueprint, make_response, send_file
from models import Parcel, Property, Sale, Account, PropertyImage
from sqlalchemy import func
from app.api.statistics import get_property_statistics
import map_module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a constant for the FastAPI URL
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# Create Blueprint for API routes
api_routes = Blueprint('api_routes', __name__)

@api_routes.route('/')
def index():
    """Render the index page with minimalist design."""
    return render_template('index_minimal.html', title="Benton County Assessor")

@api_routes.route('/export-data')
def export_data_page():
    """Render the data export page."""
    return render_template('export_data.html', title="Export Property Data")

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
        # Check database connection
        try:
            from app_setup import db
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).first()
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            db_status = "degraded"
        
        # Check for imported data
        try:
            from app_setup import db
            from models import Account, PropertyImage
            
            accounts_count = db.session.query(Account).count()
            images_count = db.session.query(PropertyImage).count()
            
            data_status = "active" if accounts_count > 0 or images_count > 0 else "empty"
            data_details = {
                "accounts": accounts_count,
                "property_images": images_count
            }
        except Exception as e:
            logger.error(f"Error checking imported data: {str(e)}")
            data_status = "unknown"
            data_details = {"error": str(e)}
        
        result = {
            "status": "operational" if db_status == "healthy" else "degraded",
            "api": {"status": "running"},
            "database": {"status": db_status},
            "imported_data": {"status": data_status, "details": data_details},
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

# Direct API endpoints for database querying
@api_routes.route('/api/run-query', methods=['POST'])
def run_query():
    """Execute a custom SQL query against the database."""
    try:
        from app_setup import db
        from sqlalchemy import text
        
        # Get the query from the request
        data = request.json
        sql_query = data.get('query')
        
        if not sql_query:
            return jsonify({
                "status": "error",
                "message": "No query provided"
            }), 400
        
        # Execute the query directly using SQLAlchemy
        result = db.session.execute(text(sql_query))
        
        # Format the result
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        return jsonify({
            "status": "success",
            "columns": columns,
            "rows": rows
        })
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to execute query: {str(e)}"
        }), 500
        
@api_routes.route('/api/parameterized-query', methods=['POST'])
def parameterized_query():
    """Execute a parameterized SQL query against the database with enhanced security."""
    try:
        from app_setup import db
        from sqlalchemy import text
        import time
        
        # Get query details from request
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
            
        # Extract parameters
        db_type = data.get('db', 'postgres')
        query = data.get('query')
        params = data.get('params', [])
        param_style = data.get('param_style', 'format')
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        security_level = data.get('security_level', 'medium')
        
        if not query:
            return jsonify({
                "status": "error",
                "message": "No SQL query provided"
            }), 400
            
        # Start timing execution
        start_time = time.time()
        
        # Basic security check
        if security_level != 'none':
            # Define patterns that might indicate SQL injection attempts
            dangerous_patterns = [
                r';\s*DROP', r';\s*DELETE', r';\s*UPDATE', r';\s*INSERT',
                r'--', r'/\*', r'\bOR\s+1\s*=\s*1\b', r'\bOR\s+\'1\'\s*=\s*\'1\'\b',
                r'\bUNION\s+SELECT\b', r'\bEXEC\b', r'\bXP_\w+\b'
            ]
            
            # Check for dangerous patterns
            import re
            for pattern in dangerous_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return jsonify({
                        "status": "error",
                        "message": "Potentially unsafe query detected",
                        "execution_time": time.time() - start_time
                    }), 403
        
        # For direct database execution, use SQLAlchemy
        try:
            # Format parameters based on style and SQL driver requirements
            if param_style == 'named':
                # Named parameters - convert list to dict if needed
                if isinstance(params, list):
                    # Extract parameter names from query like :param1, :param2, etc.
                    import re
                    param_names = re.findall(r':(\w+)', query)
                    if len(param_names) == len(params):
                        params = {name: value for name, value in zip(param_names, params)}
                    else:
                        return jsonify({
                            "status": "error",
                            "message": "Parameter count mismatch",
                            "execution_time": time.time() - start_time
                        }), 400
                        
                # Execute with named parameters
                result = db.session.execute(text(query), params)
            else:
                # Format query to use SQLAlchemy placeholders
                if '%s' in query:
                    # Convert %s format to SQLAlchemy's :param format
                    import re
                    param_count = query.count('%s')
                    param_names = [f'param{i}' for i in range(param_count)]
                    
                    # Replace %s with :param0, :param1, etc.
                    for i, param_name in enumerate(param_names):
                        query = query.replace('%s', f':{param_name}', 1)
                    
                    # Convert params list to dict with param names
                    if isinstance(params, list) and len(params) == param_count:
                        params = {name: value for name, value in zip(param_names, params)}
                        result = db.session.execute(text(query), params)
                    else:
                        return jsonify({
                            "status": "error",
                            "message": "Parameter count mismatch",
                            "execution_time": time.time() - start_time
                        }), 400
                else:
                    # If query already uses SQLAlchemy-compatible placeholders
                    # or no parameters are needed
                    if isinstance(params, list) and len(params) > 0:
                        # Convert to a dictionary for SQLAlchemy
                        params = {"param" + str(i): value for i, value in enumerate(params)}
                    
                    # Execute query with parameters
                    result = db.session.execute(text(query), params)
                
            # Get column names and rows
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # Handle pagination
            if page_size:
                # Simple pagination
                total_count = len(rows)
                total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
                
                # Slice the results based on page and page_size
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                rows = rows[start_idx:end_idx]
                
                pagination = {
                    "page": page,
                    "page_size": page_size,
                    "total_records": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            else:
                pagination = None
                
            # Calculate execution time
            execution_time = time.time() - start_time
            
            return jsonify({
                "status": "success",
                "columns": columns,
                "rows": rows,
                "pagination": pagination,
                "execution_time": execution_time
            })
                
        except Exception as e:
            logger.error(f"Error executing parameterized query: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Query execution failed: {str(e)}",
                "execution_time": time.time() - start_time
            }), 500
            
    except Exception as e:
        logger.error(f"Error handling parameterized query request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Request processing failed: {str(e)}"
        }), 500

@api_routes.route('/api/nl-to-sql', methods=['POST'])
def nl_to_sql():
    """Convert natural language to SQL using our NL processing module."""
    try:
        data = request.json
        natural_language_query = data.get('query')
        db_type = data.get('db', 'postgres')
        
        if not natural_language_query:
            return jsonify({
                "status": "error",
                "message": "No natural language query provided"
            }), 400
        
        # Import the function from our nl_processing module
        from app.nl_processing import nl_to_sql as process_nl_to_sql
        
        # Process the query using our dedicated module
        result = process_nl_to_sql(natural_language_query, db_type)
        
        # Return the result
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing natural language query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process natural language query: {str(e)}"
        }), 500
        
# Direct database access routes for imported data
@api_routes.route('/api/imported-data/accounts', methods=['GET'])
def get_imported_accounts():
    """Get imported account data directly from the database."""
    try:
        # Get query parameters
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        owner_name = request.args.get('owner_name', '')
        
        # Build query
        from app_setup import db
        query = db.session.query(Account)
        
        # Apply filters
        if owner_name:
            query = query.filter(Account.owner_name.ilike(f'%{owner_name}%'))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(Account.id).offset(offset).limit(limit)
        
        # Execute query
        accounts = query.all()
        
        # Prepare response
        accounts_data = [{
            'id': account.id,
            'account_id': account.account_id,
            'owner_name': account.owner_name,
            'mailing_address': account.mailing_address,
            'mailing_city': account.mailing_city,
            'mailing_state': account.mailing_state,
            'mailing_zip': account.mailing_zip,
            'property_address': account.property_address,
            'property_city': account.property_city,
            'legal_description': account.legal_description,
            'assessment_year': account.assessment_year,
            'assessed_value': float(account.assessed_value) if account.assessed_value else None,
            'tax_amount': float(account.tax_amount) if account.tax_amount else None,
            'tax_status': account.tax_status,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'updated_at': account.updated_at.isoformat() if account.updated_at else None
        } for account in accounts]
        
        return jsonify({
            'accounts': accounts_data,
            'total': total_count,
            'offset': offset,
            'limit': limit,
        })
    except Exception as e:
        logger.error(f"Error fetching accounts data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch accounts data: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/accounts/<account_id>', methods=['GET'])
def get_imported_account(account_id):
    """Get details for a specific account directly from the database."""
    try:
        # Build query
        from app_setup import db
        account = db.session.query(Account).filter(Account.account_id == account_id).first()
        
        if not account:
            return jsonify({
                "status": "error",
                "message": f"Account with ID {account_id} not found"
            }), 404
        
        # Prepare response
        account_data = {
            'id': account.id,
            'account_id': account.account_id,
            'owner_name': account.owner_name,
            'mailing_address': account.mailing_address,
            'mailing_city': account.mailing_city,
            'mailing_state': account.mailing_state,
            'mailing_zip': account.mailing_zip,
            'property_address': account.property_address,
            'property_city': account.property_city,
            'legal_description': account.legal_description,
            'assessment_year': account.assessment_year,
            'assessed_value': float(account.assessed_value) if account.assessed_value else None,
            'tax_amount': float(account.tax_amount) if account.tax_amount else None,
            'tax_status': account.tax_status,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'updated_at': account.updated_at.isoformat() if account.updated_at else None
        }
        
        return jsonify({
            'status': 'success',
            'account': account_data
        })
    except Exception as e:
        logger.error(f"Error fetching account {account_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch account details: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/property-images', methods=['GET'])
def get_property_images():
    """Get property images data directly from the database."""
    try:
        # Get query parameters
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        property_id = request.args.get('property_id', '')
        image_type = request.args.get('image_type', '')
        
        # Build query
        from app_setup import db
        query = db.session.query(PropertyImage)
        
        # Apply filters
        if property_id:
            query = query.filter(PropertyImage.property_id.ilike(f'%{property_id}%'))
        if image_type:
            query = query.filter(PropertyImage.image_type == image_type)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(PropertyImage.id).offset(offset).limit(limit)
        
        # Execute query
        images = query.all()
        
        # Prepare response
        images_data = [{
            'id': image.id,
            'property_id': image.property_id,
            'account_id': image.account_id,
            'image_url': image.image_url,
            'image_path': image.image_path,
            'image_type': image.image_type,
            'image_date': image.image_date.isoformat() if image.image_date else None,
            'width': image.width,
            'height': image.height,
            'file_size': image.file_size,
            'file_format': image.file_format,
            'created_at': image.created_at.isoformat() if image.created_at else None,
            'updated_at': image.updated_at.isoformat() if image.updated_at else None
        } for image in images]
        
        return jsonify({
            'property_images': images_data,
            'total': total_count,
            'offset': offset,
            'limit': limit,
        })
    except Exception as e:
        logger.error(f"Error fetching property images data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch property images data: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/improvements', methods=['GET'])
def get_improvements():
    """Get property improvements data directly from the database."""
    try:
        # Get query parameters
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        property_id = request.args.get('property_id', '')
        
        # Build query
        from app_setup import db
        # Since we don't have a dedicated Improvement model,
        # we'll query from Property model which has improvement details
        query = db.session.query(Property)
        
        # Apply filters
        if property_id:
            # Filter properties that have a matching parcel ID string
            parcel = db.session.query(Parcel).filter(Parcel.parcel_id.ilike(f'%{property_id}%')).first()
            if parcel:
                query = query.filter(Property.parcel_id == parcel.id)
            else:
                # No matching parcel, return empty result
                return jsonify({
                    'improvements': [],
                    'total': 0,
                    'offset': offset,
                    'limit': limit,
                })
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(Property.id).offset(offset).limit(limit)
        
        # Execute query
        properties = query.all()
        
        # Prepare response
        # Map property attributes to improvement attributes
        improvements_data = []
        for prop in properties:
            # Get the associated parcel
            parcel = db.session.query(Parcel).filter(Parcel.id == prop.parcel_id).first()
            if parcel:
                improvements_data.append({
                    'id': prop.id,
                    'property_id': parcel.parcel_id,
                    'improvement_id': f"I-{prop.id}",  # Generate an improvement ID
                    'description': f"{prop.property_type} structure",
                    'improvement_value': float(parcel.improvement_value) if parcel.improvement_value else 0,
                    'living_area': prop.square_footage,
                    'stories': prop.stories,
                    'year_built': prop.year_built,
                    'primary_use': prop.property_type,
                    'created_at': prop.created_at.isoformat() if prop.created_at else None,
                    'updated_at': prop.updated_at.isoformat() if prop.updated_at else None
                })
        
        return jsonify({
            'improvements': improvements_data,
            'total': total_count,
            'offset': offset,
            'limit': limit,
        })
    except Exception as e:
        logger.error(f"Error fetching improvements data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch improvements data: {str(e)}"
        }), 500
        
@api_routes.route('/query-builder')
def query_builder():
    """Render the interactive query builder interface."""
    # Get database schema directly from SQLAlchemy
    try:
        from app_setup import db
        from sqlalchemy import text, inspect
        
        # Create an inspector to get database schema information
        inspector = inspect(db.engine)
        
        # Get all tables and their schema details
        db_schema = []
        for table_name in inspector.get_table_names():
            # Get column details
            for column in inspector.get_columns(table_name):
                # Get primary key info
                primary_keys = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
                is_primary_key = column['name'] in primary_keys
                
                # Get foreign key info
                foreign_keys = inspector.get_foreign_keys(table_name)
                is_foreign_key = any(column['name'] in fk.get('constrained_columns', []) for fk in foreign_keys)
                
                # Add column info to schema
                db_schema.append({
                    'table_name': table_name,
                    'column_name': column['name'],
                    'data_type': str(column['type']),
                    'is_nullable': column.get('nullable', True),
                    'is_primary_key': is_primary_key,
                    'is_foreign_key': is_foreign_key
                })
        
        # Transform schema data into a more usable format for the UI
        tables = {}
        for item in db_schema:
            table_name = item.get("table_name")
            if table_name not in tables:
                tables[table_name] = {"columns": []}
            
            tables[table_name]["columns"].append({
                "name": item.get("column_name"),
                "data_type": item.get("data_type"),
                "is_nullable": item.get("is_nullable", True),
                "is_primary_key": item.get("is_primary_key", False),
                "is_foreign_key": item.get("is_foreign_key", False)
            })
    except Exception as e:
        logger.error(f"Error fetching schema for query builder: {str(e)}")
        tables = {}
    
    return render_template(
        'query_builder.html',
        title="Interactive Query Builder",
        version="1.0.0",
        description="Build and execute SQL queries with an interactive interface",
        schema=tables
    )

@api_routes.route('/visualize')
def visualize():
    """Render the data visualization dashboard."""
    # Get current year for the template
    current_year = datetime.datetime.now().year
    
    # Get list of cities and property types for filters
    from app_setup import app, db
    with app.app_context():
        try:
            # Get distinct cities
            cities = [city[0] for city in db.session.query(Parcel.city).distinct().order_by(Parcel.city)]
            
            # Get distinct property types
            property_types = [
                p_type[0] for p_type in 
                db.session.query(Property.property_type).distinct().order_by(Property.property_type)
                if p_type[0]  # Filter out None values
            ]
        except Exception as e:
            logger.error(f"Error fetching filter options: {str(e)}")
            cities = []
            property_types = []
    
    return render_template(
        'visualize.html',
        title="MCP Assessor Agent API",
        version="1.0.0",
        current_year=current_year,
        cities=cities,
        property_types=property_types,
        description="Interactive data visualization for property assessments"
    )

@api_routes.route('/imported-data')
def imported_data():
    """Render the imported data dashboard."""
    return render_template(
        'imported_data.html',
        title="Imported Assessment Data",
        version="1.0.0",
        description="View and analyze imported property assessment data"
    )

# Data export endpoints
@api_routes.route('/api/export/accounts/<format>')
def export_accounts_route(format):
    """Export account data to CSV or Excel."""
    from export_data import export_accounts
    limit = request.args.get('limit', 1000, type=int)
    return export_accounts(format=format, limit=limit)

@api_routes.route('/api/export/improvements/<format>')
def export_improvements_route(format):
    """Export improvement data to CSV or Excel."""
    from export_data import export_improvements
    limit = request.args.get('limit', 1000, type=int)
    return export_improvements(format=format, limit=limit)

@api_routes.route('/api/export/property-images/<format>')
def export_property_images_route(format):
    """Export property image data to CSV or Excel."""
    from export_data import export_property_images
    limit = request.args.get('limit', 1000, type=int)
    return export_property_images(format=format, limit=limit)

@api_routes.route('/api/export/combined/<format>')
def export_combined_data_route(format):
    """Export combined data from multiple tables to CSV or Excel."""
    from export_data import export_combined_data
    limit = request.args.get('limit', 1000, type=int)
    return export_combined_data(format=format, limit=limit)

# API endpoints for visualization data
@api_routes.route('/api/visualization-data/summary')
def visualization_summary():
    """Get summary statistics for the visualization dashboard."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Get query parameters for filtering
            city = request.args.get('city')
            min_value = request.args.get('min_value')
            max_value = request.args.get('max_value')
            
            # Build base query with filters using Account model since we have account data
            accounts_query = Account.query
            if city:
                accounts_query = accounts_query.filter(Account.mailing_city == city)
            if min_value and hasattr(Account, 'assessed_value'):
                accounts_query = accounts_query.filter(Account.assessed_value >= float(min_value))
            if max_value and hasattr(Account, 'assessed_value'):
                accounts_query = accounts_query.filter(Account.assessed_value <= float(max_value))
            
            # Calculate statistics
            total_properties = accounts_query.count()
            avg_value = db.session.query(func.avg(Account.assessed_value)).scalar() or 0
            total_value = db.session.query(func.sum(Account.assessed_value)).scalar() or 0
            
            # We don't have real sales data, so use static values for demo
            recent_sales = 125  # Example value
            
            # For demo purposes, we're using static change indicators
            # In a real app, these would be calculated by comparing to previous periods
            properties_change = 2.5  # 2.5% increase
            value_change = 4.2       # 4.2% increase
            total_value_change = 3.8  # 3.8% increase
            sales_change = -1.5      # 1.5% decrease
            
            return jsonify({
                "status": "success",
                "total_properties": total_properties,
                "avg_value": float(avg_value),
                "total_value": float(total_value),
                "recent_sales": recent_sales,
                "properties_change": properties_change,
                "value_change": value_change,
                "total_value_change": total_value_change,
                "sales_change": sales_change
            })
        except Exception as e:
            logger.error(f"Error generating visualization summary: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate summary: {str(e)}"
            }), 500

@api_routes.route('/api/visualization-data/property-types')
def visualization_property_types():
    """Get property values by property type for visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Query average values by property type
            results = db.session.query(
                Property.property_type,
                func.avg(Parcel.total_value).label('avg_value')
            ).join(
                Parcel, Parcel.id == Property.parcel_id
            ).group_by(
                Property.property_type
            ).filter(
                Property.property_type != None  # Exclude null property types
            ).order_by(
                Property.property_type
            ).all()
            
            # Format the results
            labels = [r[0] for r in results]
            values = [float(r[1]) for r in results]
            
            return jsonify({
                "status": "success",
                "labels": labels,
                "values": values
            })
        except Exception as e:
            logger.error(f"Error generating property type data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate property type data: {str(e)}"
            }), 500

@api_routes.route('/api/visualization-data/value-distribution')
def visualization_value_distribution():
    """Get property value distribution for visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Define value ranges
            ranges = [
                (0, 100000, 'Under $100K'),
                (100000, 250000, '$100K-$250K'),
                (250000, 500000, '$250K-$500K'),
                (500000, 1000000, '$500K-$1M'),
                (1000000, float('inf'), 'Over $1M')
            ]
            
            # Count parcels in each range
            counts = []
            for min_val, max_val, label in ranges:
                count = Parcel.query.filter(
                    Parcel.total_value >= min_val,
                    Parcel.total_value < max_val
                ).count()
                counts.append(count)
            
            # Calculate percentages
            total = sum(counts)
            percentages = [count / total * 100 if total > 0 else 0 for count in counts]
            
            return jsonify({
                "status": "success",
                "labels": [label for _, _, label in ranges],
                "values": percentages
            })
        except Exception as e:
            logger.error(f"Error generating value distribution data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate value distribution data: {str(e)}"
            }), 500

@api_routes.route('/api/visualization-data/sales-history')
def visualization_sales_history():
    """Get sales history data for visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Get sales by month for the last year
            end_date = datetime.datetime.now().date()
            start_date = end_date - datetime.timedelta(days=365)
            
            # Build an array of months
            months = []
            counts = []
            current_date = start_date
            
            while current_date <= end_date:
                next_month = datetime.datetime(
                    current_date.year + (1 if current_date.month == 12 else 0),
                    (current_date.month % 12) + 1,
                    1
                ).date()
                
                # Count sales in this month
                month_sales = Sale.query.filter(
                    Sale.sale_date >= current_date,
                    Sale.sale_date < next_month
                ).count()
                
                # Format month label
                month_label = current_date.strftime('%b %Y')
                
                months.append(month_label)
                counts.append(month_sales)
                
                # Move to next month
                current_date = next_month
            
            return jsonify({
                "status": "success",
                "labels": months,
                "values": counts
            })
        except Exception as e:
            logger.error(f"Error generating sales history data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate sales history data: {str(e)}"
            }), 500

@api_routes.route('/api/visualization-data/value-trends')
def visualization_value_trends():
    """Get property value trends by year for visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Get distinct assessment years
            years = [year[0] for year in 
                    db.session.query(Parcel.assessment_year)
                    .distinct()
                    .order_by(Parcel.assessment_year)
                    .all()]
            
            avg_values = []
            property_counts = []
            
            for year in years:
                # Get average value for this year
                avg_value = db.session.query(
                    func.avg(Parcel.total_value)
                ).filter(
                    Parcel.assessment_year == year
                ).scalar() or 0
                
                # Get property count for this year
                count = Parcel.query.filter(
                    Parcel.assessment_year == year
                ).count()
                
                avg_values.append(float(avg_value))
                property_counts.append(count)
            
            return jsonify({
                "status": "success",
                "labels": years,
                "avg_values": avg_values,
                "property_counts": property_counts
            })
        except Exception as e:
            logger.error(f"Error generating value trends data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate value trends data: {str(e)}"
            }), 500

# Statistics routes
@api_routes.route('/statistics-dashboard')
def statistics_dashboard():
    """Render the property statistics dashboard page with minimalist design."""
    return render_template('statistics_dashboard_minimal.html', title="Property Statistics")

@api_routes.route('/api/statistics')
def statistics_data():
    """API endpoint to get property statistics data."""
    return get_property_statistics()

# Map visualization routes
@api_routes.route('/map')
def map_view():
    """Render the property map visualization page with minimalist design."""
    return render_template('map_view_fixed.html', title="Property Map")

@api_routes.route('/api/map/data')
def api_map_data():
    """API endpoint to get property map data with filtering and clustering."""
    return map_module.get_map_data()

@api_routes.route('/api/map/clusters')
def api_map_clusters():
    """API endpoint to get property clusters for the map."""
    return map_module.get_map_clusters()

@api_routes.route('/api/map/property-types')
def api_property_types():
    """API endpoint to get available property types."""
    return map_module.get_property_types()

@api_routes.route('/api/map/cities')
def api_cities():
    """API endpoint to get available cities."""
    return map_module.get_cities()

@api_routes.route('/api/map/property-images/<account_id>')
def api_property_images(account_id):
    """API endpoint to get property images for a specific account."""
    return map_module.get_property_images_for_map(account_id)

@api_routes.route('/api/map/value-ranges')
def api_value_ranges():
    """API endpoint to get property value ranges for filtering."""
    return map_module.get_value_ranges()

@api_routes.route('/api/visualization-data/property-locations')
def visualization_property_locations():
    """Get property location data for map visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Since we don't have parcels with latitude/longitude data,
            # we'll create demo property locations using accounts data
            accounts = db.session.query(Account).limit(50).all()
            
            # Generate property data for the map using fake locations
            # For a real application, you would need to geocode the addresses
            import random
            
            # Define a center point for the map (example: Washington state area)
            center_lat = 47.7511  # Washington state center latitude
            center_lng = -120.7401  # Washington state center longitude
            
            property_data = []
            property_types = ["Residential", "Commercial", "Agricultural", "Industrial", "Vacant Land"]
            
            for i, account in enumerate(accounts):
                # Generate a random offset from center (within about 50 miles)
                lat_offset = (random.random() - 0.5) * 0.8
                lng_offset = (random.random() - 0.5) * 0.8
                
                # Use account values where possible, and generate reasonable fake data for visualization
                property_data.append({
                    "id": account.id,
                    "parcel_id": account.account_id,
                    "address": account.property_address or f"{random.randint(100, 9999)} Main St",
                    "city": account.property_city or account.mailing_city or "Richland",
                    "state": account.mailing_state or "WA",
                    "zip_code": account.mailing_zip or "99352",
                    "total_value": float(account.assessed_value or random.randint(150000, 750000)),
                    "latitude": center_lat + lat_offset,
                    "longitude": center_lng + lng_offset,
                    "property_type": random.choice(property_types)  # We don't have this data, so generate it
                })
            
            return jsonify({
                "status": "success",
                "properties": property_data
            })
        except Exception as e:
            logger.error(f"Error generating property location data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to generate property location data: {str(e)}"
            }), 500
# Property Detail Routes
@api_routes.route('/property/<account_id>')
def property_detail(account_id):
    """Render the property detail page for a specific account."""
    try:
        from app_setup import db
        
        # Get the property data
        property_data = db.session.query(Account).filter(Account.account_id == account_id).first()
        
        if not property_data:
            return render_template('error.html', title="Property Not Found", 
                                   message=f"Property with Account ID {account_id} not found")
        
        # Get property images
        images = db.session.query(PropertyImage).filter(PropertyImage.account_id == account_id).all()
        
        # Get similar properties (same property type and city, if available)
        similar_properties = []
        if property_data.property_type and property_data.property_city:
            similar_query = db.session.query(Account).filter(
                Account.property_type == property_data.property_type,
                Account.property_city == property_data.property_city,
                Account.account_id != account_id
            ).order_by(func.random()).limit(3)
            
            similar_properties = similar_query.all()
        
        # Get neighborhood statistics
        neighborhood_stats = None
        if property_data.property_city:
            from sqlalchemy import func, cast, Numeric
            
            # Calculate statistics for properties in the same city
            stats_query = db.session.query(
                func.count().label('property_count'),
                func.avg(cast(Account.assessed_value, Numeric)).label('avg_value'),
                func.min(cast(Account.assessed_value, Numeric)).label('min_value'),
                func.max(cast(Account.assessed_value, Numeric)).label('max_value')
            ).filter(
                Account.property_city == property_data.property_city,
                Account.assessed_value.isnot(None)
            )
            
            stats = stats_query.first()
            
            # Calculate median value (simplistic approach)
            all_values = db.session.query(Account.assessed_value).filter(
                Account.property_city == property_data.property_city,
                Account.assessed_value.isnot(None)
            ).order_by(Account.assessed_value).all()
            
            median_value = 0
            if all_values:
                values = [float(val[0]) for val in all_values]
                mid = len(values) // 2
                median_value = values[mid] if len(values) % 2 != 0 else (values[mid-1] + values[mid]) / 2
            
            if stats:
                neighborhood_stats = {
                    'property_count': stats.property_count,
                    'avg_value': float(stats.avg_value) if stats.avg_value else 0,
                    'min_value': float(stats.min_value) if stats.min_value else 0,
                    'max_value': float(stats.max_value) if stats.max_value else 0,
                    'median_value': median_value
                }
        
        # Get assessment history (simulated for now since we don't have historical data)
        # In a real application, this would come from a dedicated table with assessment history
        assessment_history = []
        current_year = 2025  # Current assessment year
        
        if property_data.assessed_value and property_data.tax_amount:
            # Create simulated assessment history for the last 3 years
            current_value = float(property_data.assessed_value)
            current_tax = float(property_data.tax_amount)
            
            assessment_history.append({
                'year': current_year,
                'assessed_value': current_value,
                'tax_amount': current_tax,
                'value_change_percent': 0.0  # No change for current year
            })
            
            # Previous years with slight decreases (simulating historical data)
            for i in range(1, 4):
                # Calculate previous year's value with a random decrease between 2-6%
                decrease_factor = 0.98 - (i * 0.01)  # 2%, 3%, 4% decrease by year
                prev_value = current_value * decrease_factor
                prev_tax = current_tax * decrease_factor
                
                assessment_history.append({
                    'year': current_year - i,
                    'assessed_value': prev_value,
                    'tax_amount': prev_tax,
                    'value_change_percent': (decrease_factor - 1) * 100  # Convert to percentage
                })
            
            # Sort by year (newest first)
            assessment_history.sort(key=lambda x: x['year'], reverse=True)
        
        return render_template('property_detail.html', 
                             title=f"Property Details - {property_data.property_address}",
                             property=property_data,
                             images=images,
                             similar_properties=similar_properties,
                             neighborhood_stats=neighborhood_stats,
                             assessment_history=assessment_history)
                             
    except Exception as e:
        logger.error(f"Error loading property details: {str(e)}")
        return render_template('error.html', title="Error", 
                             message=f"Failed to load property details: {str(e)}")

# Advanced Property Search Route
@api_routes.route('/property-search')
def property_search():
    """Render the advanced property search page."""
    from app_setup import db
    
    # Get property types for dropdown
    property_types = db.session.query(Account.property_type).filter(
        Account.property_type.isnot(None)
    ).distinct().order_by(Account.property_type).all()
    
    # Get cities for dropdown
    cities = db.session.query(Account.property_city).filter(
        Account.property_city.isnot(None)
    ).distinct().order_by(Account.property_city).all()
    
    # Get value ranges for filtering
    from sqlalchemy import func
    min_value = db.session.query(func.min(Account.assessed_value)).filter(
        Account.assessed_value.isnot(None)
    ).scalar()
    
    max_value = db.session.query(func.max(Account.assessed_value)).filter(
        Account.assessed_value.isnot(None)
    ).scalar()
    
    min_value = float(min_value) if min_value else 0
    max_value = float(max_value) if max_value else 0
    
    # Initialize search results as empty
    search_results = []
    
    # Check if search parameters are provided
    property_type = request.args.get('property_type')
    city = request.args.get('city')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    owner_name = request.args.get('owner_name')
    property_address = request.args.get('property_address')
    
    # Perform search if any parameter is provided
    is_search = any([property_type, city, min_price, max_price, owner_name, property_address])
    
    if is_search:
        # Build query
        query = db.session.query(Account)
        
        # Apply filters
        if property_type:
            query = query.filter(Account.property_type == property_type)
            
        if city:
            query = query.filter(Account.property_city == city)
            
        if min_price is not None:
            query = query.filter(Account.assessed_value >= min_price)
            
        if max_price is not None:
            query = query.filter(Account.assessed_value <= max_price)
            
        if owner_name:
            query = query.filter(Account.owner_name.ilike(f'%{owner_name}%'))
            
        if property_address:
            query = query.filter(Account.property_address.ilike(f'%{property_address}%'))
            
        # Execute query with limit
        search_results = query.order_by(Account.property_address).limit(100).all()
    
    return render_template('property_search.html', 
                         title="Property Search",
                         property_types=[pt[0] for pt in property_types if pt[0]],
                         cities=[c[0] for c in cities if c[0]],
                         min_value=min_value,
                         max_value=max_value,
                         search_results=search_results,
                         is_search=is_search,
                         search_params={
                             'property_type': property_type,
                             'city': city,
                             'min_price': min_price,
                             'max_price': max_price,
                             'owner_name': owner_name,
                             'property_address': property_address
                         })
