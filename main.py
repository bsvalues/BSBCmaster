"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
It serves as the main entry point for the hybrid Flask-FastAPI application.
"""

import os
import logging
import requests
import subprocess
import threading
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app and db from app_setup
from app_setup import app, db, FASTAPI_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if API_KEY is set
api_key = os.environ.get("API_KEY")
if not api_key:
    custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
    os.environ["API_KEY"] = custom_key

# Import models for database initialization
import models

# Import routes from database.py
from database import *

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created or verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Function to seed the database if needed
def seed_database_if_needed():
    try:
        # Check if we need to seed the database
        with app.app_context():
            parcel_count = models.Parcel.query.count()
            if parcel_count == 0:
                logger.info("No parcels found in database. Running seed script...")
                subprocess.run(["python", "seed_database.py"], check=True)
                logger.info("Database seeded successfully")
            else:
                logger.info(f"Database already has {parcel_count} parcels. No seeding needed.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")

# Seed database in a separate thread to avoid blocking app startup
threading.Thread(target=seed_database_if_needed, daemon=True).start()

# Start FastAPI service as a background process
def start_fastapi_service():
    """Start the FastAPI service as a background process."""
    try:
        logger.info("Starting FastAPI service on port 8000")
        process = subprocess.Popen(
            ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor FastAPI output
        def log_fastapi_output():
            for line in iter(process.stdout.readline, ""):
                if line:
                    logger.info(f"[FastAPI] {line.strip()}")
        
        threading.Thread(target=log_fastapi_output, daemon=True).start()
        
        # Wait a moment to ensure it starts correctly
        time.sleep(3)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error(f"FastAPI failed to start (exit code {process.returncode})")
            return None
            
        logger.info("FastAPI service started successfully on port 8000")
        return process
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return None

if __name__ == "__main__":
    # Start FastAPI service
    fastapi_process = start_fastapi_service()
    
    # Wait for FastAPI to initialize
    time.sleep(3)
    
    # Start Flask application
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting Flask documentation on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)