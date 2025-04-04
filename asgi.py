"""
This file provides an ASGI adapter for our FastAPI application.
It allows running the FastAPI application with Gunicorn and uvicorn workers.
"""

from app import app

# Export as "app" for gunicorn with uvicorn workers
# Use with: gunicorn -k uvicorn.workers.UvicornWorker asgi:app