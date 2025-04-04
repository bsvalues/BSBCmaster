"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
It serves as the main entry point for the hybrid Flask-FastAPI application.
"""

import os
import logging
import requests
import subprocess
import threading
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
    default_key = "mcp_assessor_api_default_key_2024_secure_random_token_987654321"
    logger.warning(f"API_KEY not set. Using default value: {default_key}")
    os.environ["API_KEY"] = default_key

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

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting Flask documentation on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)