#!/bin/bash

# Exit on error
set -e

echo "=== Restarting MCP Assessor Agent API Services ==="

# Kill any existing processes
echo "Stopping existing processes..."
pkill -f "gunicorn" || true
pkill -f "uvicorn" || true
sleep 1

# Start FastAPI server
echo "Starting FastAPI on port 8000..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info > fastapi.log 2>&1 &
FASTAPI_PID=$!
echo "FastAPI started with PID: $FASTAPI_PID"
sleep 2

# Start Flask server
echo "Starting Flask documentation on port 5000..."
gunicorn --bind 0.0.0.0:5000 --workers 1 --log-level info main:app > flask.log 2>&1 &
FLASK_PID=$!
echo "Flask started with PID: $FLASK_PID"
sleep 1

echo "Services started successfully!"
echo "- Flask: http://localhost:5000"
echo "- FastAPI: http://localhost:8000"
echo
echo "Process IDs:"
echo "- FastAPI: $FASTAPI_PID"
echo "- Flask: $FLASK_PID"
echo
echo "Logs:"
echo "- FastAPI: fastapi.log"
echo "- Flask: flask.log"