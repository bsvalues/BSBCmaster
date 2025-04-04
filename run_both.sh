#!/bin/bash

# This script runs both the Flask and FastAPI applications in parallel

# Start FastAPI app in the background
echo "Starting FastAPI application..."
python run_api.py &
API_PID=$!

# Start Flask app in the foreground
echo "Starting Flask application..."
python main.py

# If Flask app exits, kill the FastAPI app
kill $API_PID