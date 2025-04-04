#!/bin/bash

# This script starts the FastAPI service using uvicorn
echo "Starting FastAPI service on port 8000..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload