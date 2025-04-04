#!/bin/bash
# This script runs both the Flask and FastAPI applications

# Start FastAPI in the background
echo "Starting FastAPI application on port 8000..."
python run_api.py &
FASTAPI_PID=$!

# Start Flask in the foreground
echo "Starting Flask application on port 5000..."
python main.py

# If Flask exits, kill FastAPI
kill $FASTAPI_PID