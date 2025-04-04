"""
This file provides a combined server for both Flask documentation and FastAPI backend.
It serves as the main entry point for the hybrid Flask-FastAPI application in Replit.
"""

import os
import sys
import logging
import subprocess
import threading
import time
import atexit
import signal
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("both_services.log"),
    ]
)
logger = logging.getLogger(__name__)

# Check if API_KEY is set
api_key = os.environ.get("API_KEY")
if not api_key:
    custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
    os.environ["API_KEY"] = custom_key

# Define FastAPI URL
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")
logger.info(f"FastAPI URL: {FASTAPI_URL}")

from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Import app and db from app_setup (already configured)
from app_setup import app, db

# Import models for database initialization
from models import Parcel, Property, Sale

# Ensure database tables are created
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Import routes and database blueprint
from routes import api_routes
from database import database_bp

# Register the blueprints
app.register_blueprint(api_routes)
app.register_blueprint(database_bp, url_prefix='/database')

# Function to seed the database if needed
def seed_database_if_needed():
    try:
        # We need to ensure this runs in the Flask app context
        with app.app_context():
            try:
                # Check if we need to seed the database
                parcel_count = Parcel.query.count()
                if parcel_count == 0:
                    logger.info("No parcels found in database. Running seed script...")
                    # Run in a separate process but with proper env variables
                    subprocess.run(["python", "seed_database.py"], check=True)
                    logger.info("Database seeded successfully")
                else:
                    logger.info(f"Database already has {parcel_count} parcels. No seeding needed.")
            except Exception as inner_e:
                logger.error(f"Inner error checking/seeding database: {inner_e}")
    except Exception as e:
        logger.error(f"Error in seed_database_if_needed: {e}")

# Global variables to track FastAPI process
fastapi_process = None
fastapi_thread = None

def start_fastapi():
    """Start the FastAPI service in a background thread."""
    global fastapi_thread, fastapi_process
    
    def run_server():
        """Run uvicorn server in a separate process."""
        global fastapi_process
        try:
            # Try to kill any existing process on port 8000
            try:
                subprocess.run(
                    ["fuser", "-k", "8000/tcp"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
            except Exception:
                pass
            
            # Set up environment variables for consistent database access
            env = os.environ.copy()
            
            # Important: Pass all necessary environment variables
            env["DATABASE_URL"] = os.environ.get("DATABASE_URL", "")
            env["API_KEY"] = os.environ.get("API_KEY", "")
            env["FLASK_SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "mcp_assessor_api_secure_key")
            env["FASTAPI_URL"] = FASTAPI_URL
            
            # Start FastAPI with uvicorn
            cmd = ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
            logger.info(f"Starting FastAPI service with command: {' '.join(cmd)}")
            
            fastapi_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Log the output from the process
            for line in iter(fastapi_process.stdout.readline, ""):
                logger.info(f"[FastAPI] {line.rstrip()}")
            
            # Process has ended
            return_code = fastapi_process.wait()
            logger.info(f"FastAPI process exited with code {return_code}")
            
        except Exception as e:
            logger.error(f"Error in FastAPI thread: {e}")
    
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_server)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    logger.info("FastAPI thread started")
    
    # Wait for FastAPI to start (up to 30 seconds)
    for _ in range(30):
        try:
            response = requests.get(f"{FASTAPI_URL}/health", timeout=1)
            if response.status_code == 200:
                logger.info("FastAPI is running and healthy")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    
    logger.warning("Timed out waiting for FastAPI to start")
    return fastapi_process and fastapi_process.poll() is None

# Cleanup resources when the server exits
def cleanup_on_exit(signum=None, frame=None):
    """Cleanup resources on exit."""
    logger.info("Shutting down MCP Assessor Agent API server...")
    
    if fastapi_process and fastapi_process.poll() is None:
        logger.info("Terminating FastAPI process...")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process did not terminate, killing it...")
            fastapi_process.kill()
    
    logger.info("Shutdown complete")
    
    # Exit if this was called as a signal handler
    if signum is not None:
        sys.exit(0)

# Register the cleanup function
atexit.register(cleanup_on_exit)
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# In newer Flask versions, we use this pattern for initialization
with app.app_context():
    try:
        # Try to seed database at startup
        seed_database_if_needed()
    except Exception as e:
        logger.error(f"Failed to seed database at startup: {e}")

if __name__ == "__main__":
    # Start FastAPI first
    logger.info("Starting MCP Assessor Agent API server...")
    if start_fastapi():
        logger.info("FastAPI started successfully")
    else:
        logger.error("Failed to start FastAPI")
        # Still continue to start Flask even if FastAPI fails
        # Since we're using Gunicorn for Flask in the workflow
    
    # If running directly (not via Gunicorn), start Flask
    # For workflow, Flask is started by Gunicorn
    if "gunicorn" not in os.environ.get("SERVER_SOFTWARE", ""):
        flask_port = int(os.environ.get("FLASK_PORT", 5000))
        logger.info(f"Starting Flask documentation interface on port {flask_port}")
        app.run(host="0.0.0.0", port=flask_port, debug=True, use_reloader=False)