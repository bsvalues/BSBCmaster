#!/bin/bash
# Run both FastAPI and Flask services

# Start FastAPI in the background
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Give FastAPI time to initialize
sleep 2

# Start Flask with gunicorn
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app