#!/bin/bash

# This script starts both the Flask and FastAPI services for the MCP Assessor Agent API

# Function to clean up child processes when the script exits
cleanup() {
  echo "Cleaning up processes..."
  # Kill all child processes
  pkill -P $$
  exit 0
}

# Set up trap to call cleanup function on script exit
trap cleanup EXIT INT TERM

# Start the FastAPI service in the background
echo "Starting FastAPI service on port 8000..."
uvicorn asgi:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start the Flask service - this will run in the foreground
echo "Starting Flask service on port 5000..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# Keep the script running until killed
wait