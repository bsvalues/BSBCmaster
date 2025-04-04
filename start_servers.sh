#!/bin/bash

# MCP Assessor Agent API - Server Startup Script
# This script starts both the Flask and FastAPI services

# Kill any existing processes using the ports
echo "Checking for existing processes on ports 5000 and 8000..."
if command -v lsof &> /dev/null; then
  lsof -ti:5000 | xargs kill -9 2>/dev/null || true
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  echo "Ports freed"
fi

# Make sure log directories exist
mkdir -p logs

# Start the combined server script
echo "Starting MCP Assessor Agent API servers..."
python run_both_servers.py
