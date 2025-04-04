"""
MCP Assessor Agent API - Combined Server

This file provides an optimized implementation for running both the Flask
documentation interface and the FastAPI service together for the Replit environment.
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
        logging.FileHandler("combined_server.log"),
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

# Import models and app for the Flask component
from app_setup import app as flask_app, db
import models
from database import *  # Import all routes

# Check and ensure database tables are created
with flask_app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Seed database if needed
        parcel_count = models.Parcel.query.count()
        if parcel_count == 0:
            logger.info("No parcels found. Seeding database...")
            import subprocess
            subprocess.run(["python", "seed_database.py"], check=True)
            logger.info("Database seeded successfully")
        else:
            logger.info(f"Database already contains {parcel_count} parcels. No seeding needed.")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        sys.exit(1)

# Function to start the FastAPI service
def start_fastapi():
    """Start the FastAPI service in a background thread."""
    try:
        logger.info("Starting FastAPI service on port 8000...")
        
        # Import FastAPI app
        from app import app as fastapi_app
        import uvicorn
        
        # Configure and start uvicorn server
        config = uvicorn.Config(
            app=fastapi_app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Error running FastAPI service: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Create and start FastAPI thread
fastapi_thread = threading.Thread(target=start_fastapi)
fastapi_thread.daemon = True  # Thread will exit when main program exits
fastapi_thread.start()

# Wait for FastAPI to initialize
time.sleep(2)

# Log startup information
logger.info("=" * 60)
logger.info("MCP Assessor Agent API is starting")
logger.info("FastAPI service running on port 8000")
logger.info("Flask documentation running on port 5000")
logger.info("=" * 60)

# Provide the Flask application for gunicorn
application = flask_app

# Direct execution with Flask's development server (for testing)
if __name__ == "__main__":
    try:
        # Start Flask application with its built-in server
        flask_app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Error running Flask application: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("Server shutting down")