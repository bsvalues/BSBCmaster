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
        columns = result.keys()
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

@api_routes.route('/api/nl-to-sql', methods=['POST'])
def nl_to_sql():
    """Convert natural language to SQL using OpenAI (placeholder)."""
    try:
        data = request.json
        natural_language_query = data.get('query')
        
        if not natural_language_query:
            return jsonify({
                "status": "error",
                "message": "No natural language query provided"
            }), 400
        
        # TODO: Implement OpenAI integration for NL to SQL conversion
        # For now, return a placeholder response
        return jsonify({
            "status": "error",
            "message": "Natural language to SQL conversion is not yet implemented in direct database access mode"
        }), 501
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
            property_type = request.args.get('property_type')
            min_value = request.args.get('min_value')
            max_value = request.args.get('max_value')
            
            # Build base query with filters
            parcels_query = Parcel.query
            if city:
                parcels_query = parcels_query.filter(Parcel.city == city)
            if min_value:
                parcels_query = parcels_query.filter(Parcel.total_value >= float(min_value))
            if max_value:
                parcels_query = parcels_query.filter(Parcel.total_value <= float(max_value))
            
            # Property type filter requires a join
            if property_type:
                parcels_query = parcels_query.join(Property).filter(Property.property_type == property_type)
            
            # Calculate statistics
            total_properties = parcels_query.count()
            avg_value = db.session.query(func.avg(Parcel.total_value)).scalar() or 0
            total_value = db.session.query(func.sum(Parcel.total_value)).scalar() or 0
            
            # Get recent sales (last 90 days)
            ninety_days_ago = datetime.datetime.now().date() - datetime.timedelta(days=90)
            recent_sales = Sale.query.filter(Sale.sale_date >= ninety_days_ago).count()
            
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

@api_routes.route('/api/visualization-data/property-locations')
def visualization_property_locations():
    """Get property location data for map visualization."""
    from app_setup import app, db
    with app.app_context():
        try:
            # Get properties with location data
            properties = db.session.query(
                Parcel.id,
                Parcel.parcel_id,
                Parcel.address,
                Parcel.city,
                Parcel.state,
                Parcel.zip_code,
                Parcel.total_value,
                Parcel.latitude,
                Parcel.longitude,
                Property.property_type
            ).join(
                Property, Parcel.id == Property.parcel_id
            ).filter(
                Parcel.latitude != None,
                Parcel.longitude != None
            ).limit(100).all()  # Limit to 100 properties for performance
            
            # Format property data for the map
            property_data = []
            for p in properties:
                property_data.append({
                    "id": p.id,
                    "parcel_id": p.parcel_id,
                    "address": p.address,
                    "city": p.city,
                    "state": p.state,
                    "zip_code": p.zip_code,
                    "total_value": float(p.total_value),
                    "latitude": float(p.latitude),
                    "longitude": float(p.longitude),
                    "property_type": p.property_type
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