"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
"""

import os
import logging
import asyncio
from flask import Flask, render_template, request, jsonify, redirect
from datetime import datetime

# Try importing FastAPI components
try:
    from fastapi import FastAPI
    from fastapi.middleware.wsgi import WSGIMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    logging.warning("FastAPI imports not available, API documentation will be limited")
    FASTAPI_AVAILABLE = False

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Import the database initialization function
from app.db import initialize_db

# Initialize the database connection pool
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(initialize_db())

# Create the Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='static')

# Database connection status
def test_db_connections():
    """Test connections to configured databases."""
    from app.db import test_db_connections as db_test
    return db_test()

@app.route('/')
def index():
    """Render the index page with API documentation."""
    # Get base URL for API endpoints
    base_url = request.base_url.rstrip('/')
    
    return render_template("index.html", 
                          title="MCP Assessor Agent API",
                          version="1.0.0",
                          description="API service for accessing and querying assessment data",
                          base_url=base_url,
                          current_year=datetime.now().year)

@app.route('/api/health')
def health_check():
    """Check the health of the API and its database connections."""
    db_status = test_db_connections()
    
    return jsonify({
        "status": "ok", 
        "db_connections": db_status
    })

# Create API documentation endpoint

# Create documentation endpoint
@app.route('/api/docs')
def api_docs():
    from app.db import test_db_connections
    db_status = test_db_connections()
    
    # Create API documentation
    api_endpoints = [
        {
            "path": "/api/health",
            "method": "GET",
            "description": "Check API health and database connections",
            "parameters": [],
            "responses": {
                "200": {
                    "description": "API health status",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "db_connections": {
                                "type": "object",
                                "properties": {
                                    "postgres": {"type": "boolean"},
                                    "mssql": {"type": "boolean"}
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "path": "/api/run-query",
            "method": "POST",
            "description": "Execute SQL query against specified database with pagination",
            "parameters": {
                "db": {"type": "string", "required": True, "description": "Database type (mssql or postgres)"},
                "query": {"type": "string", "required": True, "description": "SQL query to execute"},
                "page": {"type": "integer", "required": False, "description": "Page number for paginated results (starting from 1)"},
                "page_size": {"type": "integer", "required": False, "description": "Number of records per page"}
            },
            "responses": {
                "200": {"description": "Query results with pagination metadata"},
                "400": {"description": "Bad request - invalid query or parameters"},
                "500": {"description": "Database error"}
            }
        },
        {
            "path": "/api/nl-to-sql",
            "method": "POST",
            "description": "Convert natural language to SQL query",
            "parameters": {
                "db": {"type": "string", "required": True, "description": "Database type (mssql or postgres)"},
                "prompt": {"type": "string", "required": True, "description": "Natural language prompt to convert to SQL"}
            },
            "responses": {
                "200": {"description": "Translated SQL query"},
                "400": {"description": "Bad request - missing parameters"},
                "500": {"description": "Translation error"}
            }
        },
        {
            "path": "/api/discover-schema",
            "method": "GET",
            "description": "Discover database schema",
            "parameters": {
                "db": {"type": "string", "required": True, "description": "Database type (mssql or postgres)"}
            },
            "responses": {
                "200": {"description": "Database schema information"},
                "400": {"description": "Bad request - invalid parameters"},
                "500": {"description": "Schema discovery error"}
            }
        },
        {
            "path": "/api/schema-summary",
            "method": "GET",
            "description": "Get a summarized view of the database schema",
            "parameters": {
                "db": {"type": "string", "required": True, "description": "Database type (mssql or postgres)"},
                "prefix": {"type": "string", "required": False, "description": "Optional table name prefix to filter by"}
            },
            "responses": {
                "200": {"description": "Schema summary information"},
                "400": {"description": "Bad request - invalid parameters"},
                "500": {"description": "Schema summary error"}
            }
        }
    ]
    
    return jsonify({
        "title": "MCP Assessor Agent API",
        "version": "1.1.0",
        "description": "API for executing SQL queries and exploring database schemas with robust security",
        "endpoints": api_endpoints,
        "status": "ok",
        "db_connections": db_status
    })

# Initialize FastAPI endpoints
@app.route('/api/run-query', methods=['POST'])
def run_sql_query():
    from app.db import get_postgres_connection, is_safe_query
    from flask import request
    
    # Get JSON data from request
    data = request.get_json()
    if not data or 'db' not in data or 'query' not in data:
        return jsonify({
            "status": "error",
            "detail": "Missing required fields: db, query"
        }), 400
    
    # Validate query
    if not is_safe_query(data['query']):
        return jsonify({
            "status": "error",
            "detail": "Operation not permitted in this query"
        }), 400
    
    try:
        if data['db'] == 'postgres':
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(data['query'])
                    rows = cursor.fetchall()
                    if cursor.description:  # Check if there's a result set
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in rows]
                    else:
                        # For non-SELECT queries
                        results = []
            
            total_count = len(results)
            
            # Implement pagination
            page = data.get('page', 1)
            page_size = data.get('page_size', 50)
            
            # Calculate offset and limit
            offset = (page - 1) * page_size
            end = offset + page_size
            
            # Get paginated results
            paginated_results = results[offset:end]
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
            has_next = page < total_pages
            has_prev = page > 1
            
            pagination = {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None
            }
            
            return jsonify({
                "status": "success", 
                "data": paginated_results,
                "count": total_count,
                "pagination": pagination
            })
        else:
            return jsonify({
                "status": "error",
                "detail": "Database not configured or not supported"
            }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "detail": f"Database error: {str(e)}"
        }), 500

@app.route('/api/nl-to-sql', methods=['POST'])
def nl_to_sql():
    from flask import request
    
    # Get JSON data from request
    data = request.get_json()
    if not data or 'db' not in data or 'prompt' not in data:
        return jsonify({
            "status": "error",
            "detail": "Missing required fields: db, prompt"
        }), 400
    
    try:
        # This would normally call an LLM service
        # Simulated response for demonstration
        if data['db'] == "postgres":
            # Example implementation - in a real system, this would call an LLM
            if "parcel" in data['prompt'].lower() and "value" in data['prompt'].lower():
                simulated_sql = "SELECT * FROM parcels WHERE total_value > 500000 LIMIT 100"
            else:
                simulated_sql = f"SELECT * FROM properties LIMIT 50"
        else:
            simulated_sql = f"SELECT TOP 50 * FROM properties"
        
        return jsonify({
            "status": "success", 
            "sql": simulated_sql
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "detail": f"Error processing natural language query: {str(e)}"
        }), 500

@app.route('/api/discover-schema')
def discover_schema():
    from app.db import get_postgres_connection
    from flask import request
    
    db = request.args.get('db')
    if not db or db not in ['mssql', 'postgres']:
        return jsonify({
            "status": "error",
            "detail": "Invalid or missing db parameter (must be 'mssql' or 'postgres')"
        }), 400
    
    try:
        if db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            table_name, 
                            column_name, 
                            data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public'
                    """)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
            
            # Add pagination metadata for consistency
            total_count = len(results)
            
            # Use default pagination values
            page = 1
            page_size = total_count  # Show all results by default
            
            # Calculate pagination metadata
            total_pages = 1
            
            pagination = {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": False,
                "has_prev": False,
                "next_page": None,
                "prev_page": None
            }
            
            return jsonify({
                "status": "success", 
                "db_schema": results,
                "count": total_count,
                "pagination": pagination
            })
        else:
            return jsonify({
                "status": "error",
                "detail": "Database not configured or not supported"
            }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "detail": f"Error discovering schema: {str(e)}"
        }), 500

@app.route('/api/schema-summary')
def schema_summary():
    from app.db import get_postgres_connection
    from flask import request
    
    db = request.args.get('db')
    prefix = request.args.get('prefix', '')
    
    if not db or db not in ['mssql', 'postgres']:
        return jsonify({
            "status": "error",
            "detail": "Invalid or missing db parameter (must be 'mssql' or 'postgres')"
        }), 400
    
    try:
        table_summaries = []
        
        if db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    # Get list of tables
                    if prefix:
                        cursor.execute("""
                            SELECT DISTINCT table_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name LIKE %s
                            ORDER BY table_name
                        """, (f"{prefix}%",))
                    else:
                        cursor.execute("""
                            SELECT DISTINCT table_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                            ORDER BY table_name
                        """)
                    
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get column info for each table
                    for table in tables:
                        cursor.execute("""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        
                        columns = [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]
                        table_summaries.append(f"{table}: {', '.join(columns)}")
            
            # Add pagination metadata for consistency
            total_count = len(table_summaries)
            
            # Use default pagination values
            page = 1
            page_size = total_count  # Show all results by default
            
            # Calculate pagination metadata
            total_pages = 1
            
            pagination = {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": False,
                "has_prev": False,
                "next_page": None,
                "prev_page": None
            }
            
            return jsonify({
                "status": "success", 
                "summary": table_summaries,
                "count": total_count,
                "pagination": pagination
            })
        else:
            return jsonify({
                "status": "error",
                "detail": "Database not configured or not supported"
            }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "detail": f"Error getting schema summary: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)