#!/bin/bash

# Load environment variables
source .env 2>/dev/null

# Start FastAPI service
echo "Starting FastAPI service on port 8000..."
uvicorn asgi:app --host 0.0.0.0 --port 8000
