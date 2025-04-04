#!/bin/bash

# Start both Flask and FastAPI services

# Start the Flask service in the background
echo "Starting Flask service..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app &
FLASK_PID=$!

# Start the FastAPI service in the background
echo "Starting FastAPI service..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

# Handle shutdown signals
handle_shutdown() {
    echo "Shutting down services..."
    kill $FLASK_PID $FASTAPI_PID
    exit 0
}

# Register the shutdown handler
trap handle_shutdown SIGINT SIGTERM

# Keep the script running
echo "Both services are running. Press Ctrl+C to stop."
wait $FLASK_PID $FASTAPI_PID