"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
It serves as the main entry point for the hybrid Flask-FastAPI application.
"""

import os
import logging
import subprocess
import threading
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flask.log"),
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

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

# Initialize the app with the extension
db.init_app(app)

# Import models for database initialization
from models import Parcel, Property, Sale

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created or verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Import routes from database.py
from database import *

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

# In newer Flask versions, we use this pattern instead of before_first_request
with app.app_context():
    try:
        # Try to seed database at startup
        seed_database_if_needed()
    except Exception as e:
        logger.error(f"Failed to seed database at startup: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting Flask documentation on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)