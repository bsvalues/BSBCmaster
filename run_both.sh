#!/bin/bash

# Start FastAPI in the background
python -m uvicorn asgi:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Give FastAPI a moment to start
sleep 2

# Start Flask with Gunicorn
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app