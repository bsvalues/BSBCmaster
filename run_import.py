"""
Script to run the data import process directly.
"""

import logging
from import_attached_data import import_all_data
from app_setup import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting data import...")
    with app.app_context():
        # Import data from attached_assets directory
        results = import_all_data()
        logger.info(f"Import complete. Results: {results}")