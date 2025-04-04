#!/bin/bash

# Start the FastAPI service
echo "Starting FastAPI service..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload