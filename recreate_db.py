"""
Script to recreate all database tables based on model definitions.
"""

import logging
from app_setup import app, db
import models  # This imports our model definitions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_tables():
    """Drop all tables and recreate them based on model definitions."""
    with app.app_context():
        logger.info("Dropping all tables...")
        db.drop_all()
        
        logger.info("Creating all tables...")
        db.create_all()
        
        logger.info("Database tables recreated successfully.")

if __name__ == "__main__":
    recreate_tables()