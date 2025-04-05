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
        
# Proxy routes for imported data endpoints
@api_routes.route('/api/imported-data/accounts', methods=['GET'])
def proxy_imported_accounts():
    """Proxy for the FastAPI imported-data/accounts endpoint."""
    try:
        # Forward the request to FastAPI with query parameters
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.get(
            f"{FASTAPI_URL}/api/imported-data/accounts",
            params=request.args,
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying imported-data/accounts: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/accounts/<account_id>', methods=['GET'])
def proxy_imported_account(account_id):
    """Proxy for the FastAPI imported-data/accounts/{account_id} endpoint."""
    try:
        # Forward the request to FastAPI
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.get(
            f"{FASTAPI_URL}/api/imported-data/accounts/{account_id}",
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying imported-data/accounts/{account_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/property-images', methods=['GET'])
def proxy_imported_property_images():
    """Proxy for the FastAPI imported-data/property-images endpoint."""
    try:
        # Forward the request to FastAPI with query parameters
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.get(
            f"{FASTAPI_URL}/api/imported-data/property-images",
            params=request.args,
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying imported-data/property-images: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500

@api_routes.route('/api/imported-data/improvements', methods=['GET'])
def proxy_imported_improvements():
    """Proxy for the FastAPI imported-data/improvements endpoint."""
    try:
        # Forward the request to FastAPI with query parameters
        headers = {
            'X-API-Key': request.headers.get('X-API-Key', os.environ.get('API_KEY', ''))
        }
        response = requests.get(
            f"{FASTAPI_URL}/api/imported-data/improvements",
            params=request.args,
            headers=headers
        )
        
        # Return the response from FastAPI
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error proxying imported-data/improvements: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to proxy request: {str(e)}"
        }), 500
        
@api_routes.route('/query-builder')
def query_builder():
    """Render the interactive query builder interface."""
    # Get database schema for the query builder
    try:
        # Get schema from FastAPI
        headers = {'X-API-Key': os.environ.get('API_KEY', '')}
        schema_response = requests.get(
            f"{FASTAPI_URL}/api/discover-schema?db=postgres", 
            headers=headers
        )
        
        if schema_response.status_code == 200:
            schema_data = schema_response.json()
        else:
            schema_data = {"status": "error", "db_schema": []}
            logger.error(f"Error fetching schema: {schema_response.text}")
    except Exception as e:
        schema_data = {"status": "error", "db_schema": []}
        logger.error(f"Error fetching schema for query builder: {str(e)}")
    
    # Transform schema data into a more usable format for the UI
    tables = {}
    for item in schema_data.get("db_schema", []):
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