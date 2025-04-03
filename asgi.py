"""
This file provides an ASGI adapter for our FastAPI application.
It allows running the FastAPI application with Gunicorn and uvicorn workers.
"""

from app import create_app

# Create the FastAPI app
app = create_app()

# Export as "app" for gunicorn with uvicorn workers
# Use with: gunicorn -k uvicorn.workers.UvicornWorker asgi:app