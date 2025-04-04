"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
It serves as the main entry point for the hybrid Flask-FastAPI application.
"""

import os
import logging
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the application and database
from database import app, db

# Import models to ensure they are registered
from database import Parcel, Property, Sale

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Add CORS to the app
CORS(app)

# Create all database tables (just in case)
with app.app_context():
    db.create_all()
    
    # Log database initialization
    logging.info("Database tables initialized")
    logging.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
# This is the main entry point for the application
# The Flask app serves the main documentation UI at port 5000
# The FastAPI app serves the API endpoints at port 8000 (in run_api.py)
if __name__ == "__main__":
    logging.info("Starting Flask application for documentation UI")
    logging.info("Documentation will be available at http://localhost:5000")
    logging.info("API will be available at http://localhost:8000/api")
    app.run(host="0.0.0.0", port=5000, debug=True)