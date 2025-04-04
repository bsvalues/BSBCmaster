"""
This module sets up the Flask application and database connection.
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "mcp_assessor_api_secure_key")

# Set the FastAPI URL for proxying requests
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Initialize database
with app.app_context():
    @app.before_request
    def create_tables_before_first_request():
        """Initialize database tables before first request."""
        # Use function attribute to track if tables have been created
        if not getattr(create_tables_before_first_request, 'tables_created', False):
            db.create_all()
            app.logger.info("Database tables created successfully")
            create_tables_before_first_request.tables_created = True