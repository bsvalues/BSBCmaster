#!/bin/bash

# Load environment variables
source .env 2>/dev/null

# Set the environment variable to tell Flask where to find FastAPI
# Use 0.0.0.0 instead of localhost for proper internal communication in Replit
export FASTAPI_URL="http://0.0.0.0:8000"

# Function to clean up child processes on exit
cleanup() {
    echo "Shutting down services..."
    # Kill all child processes
    pkill -P $$
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Start FastAPI service in the background
echo "Starting FastAPI service on port 8000..."
python run_api.py &

# Wait for FastAPI to initialize
echo "Waiting for FastAPI to initialize..."
sleep 10

# Start Flask service in the foreground
echo "Starting Flask documentation on port 5000..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# If gunicorn exits, clean up
cleanup
