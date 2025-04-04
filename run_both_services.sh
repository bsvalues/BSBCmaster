#!/bin/bash

# Set environment variable for Flask-FastAPI communication
export FASTAPI_URL="http://127.0.0.1:8000"

# Start FastAPI service in background
echo "Starting FastAPI service..."
python -m uvicorn asgi:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &
FASTAPI_PID=$!

# Give FastAPI time to initialize
sleep 5

# Start Flask service in foreground
echo "Starting Flask application..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
