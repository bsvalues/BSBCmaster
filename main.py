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
from sqlalchemy import func
import requests
from urllib.parse import urlparse
from flask import jsonify, request, Blueprint

from app_setup import app, db, create_tables
from routes import api_routes
from models import Parcel, Property, Sale, Account, PropertyImage

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
        from sqlalchemy import text
        try:
            # Try to query the accounts table
            result = text("SELECT COUNT(*) FROM accounts")
            count = db.session.execute(result).scalar()
            
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
            # Check database connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
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
            
            # Since we don't have a dedicated model for improvements,
            # we'll query the database directly
            from sqlalchemy import text
            
            # Build query conditions
            conditions = ""
            if property_id:
                conditions = f" WHERE property_id LIKE '%{property_id}%'"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM improvements{conditions}"
            count_result = db.session.execute(text(count_query))
            total_count = count_result.scalar() or 0
            
            # Query improvements with pagination
            query = f"""
                SELECT * FROM improvements{conditions}
                LIMIT {limit} OFFSET {offset}
            """
            result = db.session.execute(text(query))
            
            # Convert to list of dictionaries
            improvements = []
            for row in result:
                # Convert row to dict
                improvement = dict(row._mapping)
                
                # Handle numeric values
                for key, value in improvement.items():
                    if hasattr(value, 'quantize'):  # Check if it's a Decimal
                        improvement[key] = float(value)
                
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


@app.route('/')
def index():
    """Handle the root route."""
    return """
    <h1>MCP Assessor Agent API</h1>
    <p>Welcome to the MCP Assessor Agent API. This application provides:</p>
    <ul>
        <li><a href="/api-docs">API Documentation</a> - Interactive API documentation and testing</li>
        <li><a href="/query-builder">Query Builder</a> - Build and execute SQL queries</li>
        <li><a href="/visualize">Data Visualization</a> - Interactive data visualization dashboard</li>
        <li><a href="/imported-data">Imported Assessment Data</a> - View and analyze imported property assessment data</li>
        <li><a href="/api/imported-data/accounts">API: Imported Accounts</a> - Raw API endpoint for imported account data</li>
        <li><a href="/api/imported-data/property-images">API: Property Images</a> - Raw API endpoint for property images</li>
    </ul>
    """

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