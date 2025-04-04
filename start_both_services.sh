#!/bin/bash

# Script to start both Flask and FastAPI services
# Run as: ./start_both_services.sh

echo "Starting MCP Assessor Agent API services..."

# Check if required environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL is not set. Using default from .env file."
fi

if [ -z "$API_KEY" ]; then
    echo "WARNING: API_KEY is not set. Using default from settings."
fi

# Kill any existing processes on ports 5000 and 8000
echo "Cleaning up any existing services..."
pkill -f "gunicorn --bind 0.0.0.0:5000" || true
pkill -f "uvicorn asgi:app --host 0.0.0.0 --port 8000" || true

# Start FastAPI service in the background
echo "Starting FastAPI service on port 8000..."
python -m uvicorn asgi:app --host 0.0.0.0 --port 8000 --reload > fastapi.log 2>&1 &
FASTAPI_PID=$!

# Wait for FastAPI to initialize
echo "Waiting for FastAPI to initialize..."
sleep 5

# Check if FastAPI started successfully
if ! ps -p $FASTAPI_PID > /dev/null; then
    echo "Failed to start FastAPI service. Check fastapi.log for details."
    cat fastapi.log
    exit 1
fi

# Start Flask service in the foreground
echo "Starting Flask documentation on port 5000..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app