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

# API endpoints that would be implemented in a FastAPI app
# These are stubs that return documentation information
@app.route('/api/run-query', methods=['POST'])
def run_sql_query():
    return jsonify({
        "status": "info",
        "message": "This is a documentation endpoint. In the actual implementation, this would execute a SQL query."
    })

@app.route('/api/nl-to-sql', methods=['POST'])
def nl_to_sql():
    return jsonify({
        "status": "info",
        "message": "This is a documentation endpoint. In the actual implementation, this would convert natural language to SQL."
    })

@app.route('/api/discover-schema')
def discover_schema():
    return jsonify({
        "status": "info",
        "message": "This is a documentation endpoint. In the actual implementation, this would return the database schema."
    })

@app.route('/api/schema-summary')
def schema_summary():
    return jsonify({
        "status": "info",
        "message": "This is a documentation endpoint. In the actual implementation, this would return a summary of the database schema."
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)