"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
"""

import os
import logging
from flask_cors import CORS
from datetime import datetime

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
    
# This is the main entry point for the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)