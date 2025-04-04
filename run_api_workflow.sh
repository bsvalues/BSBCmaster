#!/bin/bash

# This script runs the FastAPI application using uvicorn

# Start the FastAPI application
echo "Starting FastAPI service on port 8000..."
uvicorn asgi:app --host 0.0.0.0 --port 8000 --reload