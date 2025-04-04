"""
This file provides an ASGI adapter for our FastAPI application.
It allows running the FastAPI application with Gunicorn and uvicorn workers.
"""

from app import app as fastapi_app

# Export as "app" for gunicorn with uvicorn workers
# Use with: gunicorn -k uvicorn.workers.UvicornWorker asgi:app
app = fastapi_app