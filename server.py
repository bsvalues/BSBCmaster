"""
MCP Assessor Agent API - Workflow-Compatible Server

This script starts both the Flask documentation interface and FastAPI service
using a single-process approach for the Replit workflow environment.
"""

import os
import logging
import threading
import time
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log"),
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set default API key if not present
api_key = os.environ.get("API_KEY")
if not api_key:
    custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
    os.environ["API_KEY"] = custom_key

# Import models to ensure tables are created
from app_setup import app, db
import models
from database import *  # Import all routes

# Check database and create tables if needed
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        sys.exit(1)

# Function to seed the database if needed
def seed_database_if_needed():
    """Seed the database if no data exists."""
    try:
        with app.app_context():
            parcel_count = models.Parcel.query.count()
            if parcel_count == 0:
                logger.info("No parcels found in database. Running seed script...")
                import subprocess
                subprocess.run(["python", "seed_database.py"], check=True)
                logger.info("Database seeded successfully")
            else:
                logger.info(f"Database already has {parcel_count} parcels. No seeding needed.")
    except Exception as e:
        logger.error(f"Error checking/seeding database: {e}")

# Function to start the FastAPI service
def start_fastapi():
    """Start the FastAPI service in a background thread."""
    try:
        logger.info("Starting FastAPI service on port 8000...")
        
        from app import app as fastapi_app
        import uvicorn
        
        uvicorn_config = uvicorn.Config(
            app=fastapi_app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
        # Using a custom thread run method to avoid blocking
        def run_server():
            server = uvicorn.Server(uvicorn_config)
            server.run()
        
        return run_server
    except Exception as e:
        logger.error(f"Error setting up FastAPI server: {str(e)}")
        return None

# Start thread to check and seed database
seed_thread = threading.Thread(target=seed_database_if_needed)
seed_thread.daemon = True
seed_thread.start()

# Get the FastAPI runner function
fastapi_runner = start_fastapi()

# Start thread for FastAPI service if setup was successful
if fastapi_runner:
    fastapi_thread = threading.Thread(target=fastapi_runner)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    logger.info("FastAPI thread started successfully")
else:
    logger.error("Failed to set up FastAPI runner")

# Allow time for FastAPI to initialize
time.sleep(2)

# Log startup status
logger.info("MCP Assessor Agent API services starting:")
logger.info("- FastAPI running on port 8000")
logger.info("- Flask documentation running on port 5000")

# Provide Flask app for Gunicorn to use
application = app

# For direct execution (though typically run via gunicorn)
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server shutting down")