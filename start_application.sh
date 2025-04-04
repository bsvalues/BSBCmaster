#!/bin/bash

# This script starts the MCP Assessor Agent API
# - Flask documentation on port 5000
# - FastAPI service on port 8000

echo "Starting MCP Assessor Agent API..."

# Use the configured workflow to start the application
echo "Starting both services using Replit workflow..."
./start_services.sh