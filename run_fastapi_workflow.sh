#!/bin/bash
# Start FastAPI service
echo "Starting FastAPI service..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000
