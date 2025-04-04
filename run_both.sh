#!/bin/bash

# Export environment variables
export $(cat .env)

# Run FastAPI service in the background
python run_api.py &
FASTAPI_PID=$!

# Run Flask service
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# Kill FastAPI service when Flask service is killed
kill $FASTAPI_PID