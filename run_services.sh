#!/bin/bash

# Run FastAPI and Flask services together
# This script starts both services in a coordinated way

echo "Starting MCP Assessor Agent API services..."

# Kill any existing processes on ports 5000 and 8000
echo "Cleaning up any existing services..."
pkill -f "gunicorn --bind 0.0.0.0:5000" || true
pkill -f "uvicorn asgi:app --host 0.0.0.0 --port 8000" || true

# Start FastAPI service in the background
echo "Starting FastAPI service on port 8000..."
python -m uvicorn asgi:app --host 0.0.0.0 --port 8000 --reload > fastapi.log 2>&1 &
FASTAPI_PID=$!

# Wait a bit for FastAPI to initialize
echo "Waiting for FastAPI to initialize..."
sleep 5

# Check if FastAPI started successfully
if ! ps -p $FASTAPI_PID > /dev/null; then
    echo "Failed to start FastAPI service. Check fastapi.log for details."
    exit 1
fi

# Start Flask service in the foreground
echo "Starting Flask documentation on port 5000..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app