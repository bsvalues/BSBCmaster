#!/bin/bash

# Start both FastAPI and Flask services for the MCP Assessor Agent API

# Kill any existing processes on ports 5000 and 8000
echo "Checking for existing services..."
fuser -k 5000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
echo "Ports freed."

# Start FastAPI in the background
echo "Starting FastAPI service on port 8000..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload > fastapi_output.log 2>&1 &
FASTAPI_PID=$!
echo "FastAPI process started with PID: $FASTAPI_PID"

# Wait a moment for FastAPI to initialize
echo "Waiting for FastAPI to initialize..."
sleep 5

# Start Flask using gunicorn
echo "Starting Flask documentation on port 5000..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# When gunicorn exits, kill the FastAPI process too
echo "Stopping FastAPI process..."
kill $FASTAPI_PID 2>/dev/null || true

echo "All services stopped."
