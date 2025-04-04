#!/bin/bash
# Start both FastAPI and Flask applications

# Start FastAPI in the background
echo "Starting FastAPI service..."
uvicorn app:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Start Flask in the foreground
echo "Starting Flask service..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# Cleanup
kill $FASTAPI_PID