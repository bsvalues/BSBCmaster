"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from datetime import datetime

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create the Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='static')

# Database connection status
def test_db_connections():
    """Test connections to configured databases."""
    # For now, just return static values
    # In a real implementation, this would test actual connections
    return {
        "postgres": os.environ.get("PGHOST") is not None,
        "mssql": False  # MS SQL not configured
    }

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

# Import the FastAPI app and create ASGI to WSGI adapter
from asgi import app as fastapi_app
from fastapi.middleware.wsgi import WSGIMiddleware

# Mount the FastAPI app on the Flask app at the /api path
fastapi_app.mount("/flask", WSGIMiddleware(app))

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
            truncated = total_count > 50
            limited_results = results[:50]
            
            return jsonify({
                "status": "success", 
                "data": limited_results,
                "count": total_count,
                "truncated": truncated
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
            
            return jsonify({"status": "success", "db_schema": results})
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
            
            return jsonify({"status": "success", "summary": table_summaries})
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