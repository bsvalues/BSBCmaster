#!/bin/bash
# Combined script to start both FastAPI and Flask services for the MCP Assessor Agent API

# Load environment variables
source .env 2>/dev/null || true

# Set the FastAPI URL environment variable if not already set
export FASTAPI_URL=${FASTAPI_URL:-http://localhost:8000}
echo "FastAPI URL set to: $FASTAPI_URL"

# Create a named pipe for FastAPI logs
FASTAPI_LOG_PIPE="/tmp/fastapi_logs_pipe"
rm -f $FASTAPI_LOG_PIPE
mkfifo $FASTAPI_LOG_PIPE

# Start FastAPI service in the background with logs
echo "Starting FastAPI service on port 8000..."
(python -m uvicorn app:app --host 0.0.0.0 --port 8000 > $FASTAPI_LOG_PIPE 2>&1) &
FASTAPI_PID=$!

# Read from the named pipe and prefix with "FastAPI: " in a separate process
(while read -r line; do echo "FastAPI: $line"; done < $FASTAPI_LOG_PIPE) &
LOG_READER_PID=$!

# Wait for FastAPI to start (up to 15 seconds)
echo "Waiting for FastAPI service to start..."
MAX_ATTEMPTS=15
for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "FastAPI service started successfully (attempt $i/$MAX_ATTEMPTS)"
        break
    fi
    
    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "Warning: FastAPI service might not be running properly after $MAX_ATTEMPTS attempts"
        # Continue anyway - we'll start Flask which will report errors when proxying
    fi
    
    echo "Waiting for FastAPI to start (attempt $i/$MAX_ATTEMPTS)..."
    sleep 1
done

# Start Flask in the foreground
echo "Starting Flask documentation on port 5000..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload --access-logfile - --error-logfile - main:app