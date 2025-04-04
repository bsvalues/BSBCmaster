"""
This file provides an ASGI adapter for our FastAPI application.
It allows running the FastAPI application with Gunicorn and uvicorn workers.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fastapi.log"),
    ]
)
logger = logging.getLogger(__name__)

try:
    # Import the FastAPI app
    from app import app as fastapi_app
    # Export as "app" for gunicorn with uvicorn workers
    # Use with: gunicorn -k uvicorn.workers.UvicornWorker asgi:app
    app = fastapi_app
    logger.info("FastAPI application loaded successfully")
except Exception as e:
    logger.error(f"Error loading FastAPI application: {str(e)}", exc_info=True)
    raise