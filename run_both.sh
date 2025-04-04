#!/bin/bash

# This script runs both the Flask and FastAPI applications in parallel

# Start FastAPI app in the background using uvicorn directly
echo "Starting FastAPI application on port 8000..."
python run_api.py &
API_PID=$!

# Give the FastAPI app time to start up
sleep 2
echo "FastAPI service should be running on port 8000"

# Start Flask app using gunicorn
echo "Starting Flask documentation UI on port 5000..."
# Use the existing workflow command to maintain compatibility
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# Note: exec replaces the current process, so we don't need the kill command
# If this script terminates, Replit will clean up the background processes