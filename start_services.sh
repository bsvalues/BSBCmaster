#!/bin/bash

# This script starts both the Flask and FastAPI services using the workflow manager

# Set the environment variables
export FLASK_PORT=5000
export FASTAPI_PORT=8000
export FASTAPI_URL=http://0.0.0.0:8000

# Start the workflow manager
echo "Starting MCP Assessor Agent API services..."
python3 workflow.py