"""
This file provides a combined server for both Flask documentation and FastAPI backend.
It serves as the main entry point for the hybrid Flask-FastAPI application in Replit.
"""

import os
import sys
import signal
import logging
import threading
import subprocess
import time
import requests
from urllib.parse import urlparse

from app_setup import app, db, create_tables
from routes import api_routes

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
    
    # Start the FastAPI process
    fastapi_process = start_fastapi()
    
    # Make sure it started
    logger.info("Started FastAPI process with PID: %s", 
                fastapi_process.pid if fastapi_process else "unknown")
    
    try:
        # Run the Flask app
        app.run(host="0.0.0.0", port=FLASK_PORT, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        cleanup_on_exit()
    finally:
        # Clean up the FastAPI process when Flask exits
        if fastapi_process:
            fastapi_process.terminate()