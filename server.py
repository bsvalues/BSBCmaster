"""
MCP Assessor Agent API - Workflow-Compatible Server

This script starts both the Flask documentation interface and FastAPI service
using a single-process approach for the Replit workflow environment.
"""

import os
import sys
import subprocess
import threading
import time
import signal
import logging
import requests
from datetime import datetime
import atexit
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log")
    ]
)
logger = logging.getLogger(__name__)

# Check required environment variables
if not os.environ.get("DATABASE_URL"):
    logger.warning("DATABASE_URL environment variable not set")
    # This is fine in development, but should be required in production

# Setup API key if not provided
api_key = os.environ.get("API_KEY")
if not api_key:
    custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
    os.environ["API_KEY"] = custom_key

# Set FastAPI URL for Flask to connect to
fastapi_url = os.environ.get("FASTAPI_URL", "http://localhost:8000")
os.environ["FASTAPI_URL"] = fastapi_url
logger.info(f"FastAPI URL set to: {fastapi_url}")

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Database setup for Flask
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

# Initialize the app with the extension
db.init_app(app)

# Import models 
from models import Parcel, Property, Sale

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created or verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Health endpoint to verify Flask is working
@app.route("/health")
def health():
    """Health check endpoint for Flask."""
    try:
        # Check database connection
        with app.app_context():
            db_status = "connected" if db.engine.execute("SELECT 1").scalar() == 1 else "error"
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        db_status = f"error: {str(e)}"

    # Check FastAPI connection
    fastapi_status = "unknown"
    try:
        fastapi_response = requests.get(f"{fastapi_url}/health", timeout=2)
        if fastapi_response.status_code == 200:
            fastapi_status = "connected"
        else:
            fastapi_status = f"error: status code {fastapi_response.status_code}"
    except requests.exceptions.RequestException as e:
        fastapi_status = f"error: {str(e)}"

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "fastapi": fastapi_status
    })

# Simple index route
@app.route("/")
def index():
    """Simple index route for Flask."""
    return render_template("index.html", fastapi_url=fastapi_url)

# Import routes after app creation
from database import *

# Function to seed the database if needed
def seed_database_if_needed():
    """Seed the database if no data exists."""
    try:
        # Check if we need to seed the database
        with app.app_context():
            try:
                parcel_count = Parcel.query.count()
                if parcel_count == 0:
                    logger.info("No parcels found in database. Running seed script...")
                    subprocess.run(["python", "seed_database.py"], check=True)
                    logger.info("Database seeded successfully")
                else:
                    logger.info(f"Database already has {parcel_count} parcels. No seeding needed.")
            except Exception as e:
                logger.error(f"Error checking/seeding database: {e}")
    except Exception as e:
        logger.error(f"Error in seed_database_if_needed: {e}")

# FastAPI thread
fastapi_thread = None
fastapi_process = None

def start_fastapi():
    """Start the FastAPI service in a background thread."""
    global fastapi_thread, fastapi_process
    
    def run_server():
        """Run uvicorn server in a separate process."""
        global fastapi_process
        try:
            # Kill any existing process on port 8000
            try:
                subprocess.run(
                    ["fuser", "-k", "8000/tcp"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                logger.info("Killed existing process on port 8000")
            except Exception:
                pass
            
            # Start FastAPI with uvicorn
            # Fix the command to use a different import path
            cmd = ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
            logger.info(f"Starting FastAPI service with command: {' '.join(cmd)}")
            
            fastapi_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
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
    
    # Wait for FastAPI to start
    for _ in range(30):
        try:
            response = requests.get(f"{fastapi_url}/health", timeout=1)
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

# Test function to verify FastAPI connectivity
def fastapi_test():
    """Test connectivity to the FastAPI service."""
    try:
        response = requests.get(f"{fastapi_url}/health", timeout=5)
        logger.info(f"FastAPI health response: {response.status_code}")
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"FastAPI test failed: {e}")
        return None

if __name__ == "__main__":
    # Instead of running separately, use main.py for better integration
    logger.info("Starting MCP Assessor Agent API server using main.py...")
    import main
    main.app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)