#!/bin/bash

# This script starts the MCP Assessor Agent API application with both Flask and FastAPI services

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set the environment variables (overriding .env if needed)
export FLASK_PORT=5000
export FASTAPI_PORT=8000
export FASTAPI_URL=http://localhost:8000

# Set API_KEY if not already set
if [ -z "$API_KEY" ]; then
    export API_KEY=b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e
fi

# Check if the database needs to be seeded
echo "Checking database setup..."
python seed_database.py

# Start the workflow manager to run both services
echo "Starting MCP Assessor Agent API services..."
python workflow.py