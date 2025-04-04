"""
This file provides a Flask application for documentation of the MCP Assessor Agent API.
It serves as the main entry point for the hybrid Flask-FastAPI application.
"""

import os
import logging
import requests

# Import app and db from app_setup
from app_setup import app, db, FASTAPI_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models for database initialization
import models

# Import routes from database.py
from database import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)