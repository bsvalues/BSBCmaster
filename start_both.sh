#!/bin/bash
# Script to start both FastAPI and Flask applications

# Start FastAPI in the background
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Give FastAPI time to start
sleep 5

# Start Flask using gunicorn (this will keep the shell script running)
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# If gunicorn exits, also kill the FastAPI process
kill $FASTAPI_PID
