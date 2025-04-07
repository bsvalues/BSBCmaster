"""
This file provides an ASGI adapter for our FastAPI application.
It allows running the FastAPI application with Gunicorn and uvicorn workers.
"""

import os
import logging
import sys
from app.__init__ import app as fastapi_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Make the FastAPI app instance available at the module level
# This is what Uvicorn will import when run with asgi:app
app = fastapi_app