#!/bin/bash

# This script starts both the Flask and FastAPI services
# for the MCP Assessor Agent API

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment variables from .env${NC}"
    set -o allexport
    source .env
    set +o allexport
fi

# Check for required environment variables
echo -e "${YELLOW}Checking environment variables...${NC}"
if [ -z "$API_KEY" ]; then
    echo -e "${YELLOW}API_KEY not set. Using default value.${NC}"
    export API_KEY="b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}DATABASE_URL not set. Both services may not function properly.${NC}"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}OPENAI_API_KEY not set. Natural language features will be unavailable.${NC}"
fi

# Create log directory if it doesn't exist
mkdir -p logs

# Define cleanup function for graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}Received interrupt. Shutting down services...${NC}"
    # Kill background processes
    if [ ! -z "$FLASK_PID" ]; then
        echo -e "${YELLOW}Stopping Flask (PID: $FLASK_PID)${NC}"
        kill -TERM $FLASK_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FASTAPI_PID" ]; then
        echo -e "${YELLOW}Stopping FastAPI (PID: $FASTAPI_PID)${NC}"
        kill -TERM $FASTAPI_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Register the cleanup function for SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start Flask documentation service
start_flask() {
    echo -e "\n${GREEN}Starting Flask documentation service on port 5000...${NC}"
    gunicorn --bind 0.0.0.0:5000 --workers 2 --reuse-port --reload main:app > logs/flask.log 2>&1 &
    FLASK_PID=$!
    echo -e "${BLUE}Flask service started with PID: $FLASK_PID${NC}"
    sleep 2
    
    # Check if Flask is running
    if kill -0 $FLASK_PID 2>/dev/null; then
        echo -e "${GREEN}Flask service is running successfully.${NC}"
        echo -e "${BLUE}Documentation available at: http://localhost:5000${NC}"
    else
        echo -e "${RED}Flask service failed to start. Check logs/flask.log for details.${NC}"
        cat logs/flask.log
    fi
}

# Start FastAPI service
start_fastapi() {
    echo -e "\n${GREEN}Starting FastAPI service on port 8000...${NC}"
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload > logs/fastapi.log 2>&1 &
    FASTAPI_PID=$!
    echo -e "${BLUE}FastAPI service started with PID: $FASTAPI_PID${NC}"
    sleep 2
    
    # Check if FastAPI is running
    if kill -0 $FASTAPI_PID 2>/dev/null; then
        echo -e "${GREEN}FastAPI service is running successfully.${NC}"
        echo -e "${BLUE}API available at: http://localhost:8000${NC}"
    else
        echo -e "${RED}FastAPI service failed to start. Check logs/fastapi.log for details.${NC}"
        cat logs/fastapi.log
    fi
}

# Start the services
echo -e "${GREEN}===== Starting MCP Assessor Agent API Services =====${NC}"
start_flask
start_fastapi

echo -e "\n${GREEN}All services started!${NC}"
echo -e "${BLUE}Flask documentation: http://localhost:5000${NC}"
echo -e "${BLUE}FastAPI service: http://localhost:8000${NC}"
echo -e "${BLUE}FastAPI OpenAPI docs: http://localhost:8000/api/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep the script running to handle Ctrl+C gracefully
while true; do
    # Check if both services are still running
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo -e "${RED}Flask service stopped unexpectedly. Restarting...${NC}"
        start_flask
    fi
    
    if ! kill -0 $FASTAPI_PID 2>/dev/null; then
        echo -e "${RED}FastAPI service stopped unexpectedly. Restarting...${NC}"
        start_fastapi
    fi
    
    sleep 5
done