#!/bin/bash
# Combined service script for Replit workflow

# Source environment variables
source .env 2>/dev/null || true

# Start FastAPI in the background
echo "Starting FastAPI service on port 8000..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to initialize
sleep 3
echo "FastAPI service started"

# Start Flask in the foreground (this is what the workflow will see)
echo "Starting Flask documentation on port 5000..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app