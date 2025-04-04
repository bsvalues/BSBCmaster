#!/bin/bash

# Load environment variables
source .env 2>/dev/null

# Set FastAPI URL to point to the other service
export FASTAPI_URL="http://0.0.0.0:8000"

# Start Flask service (gunicorn)
echo "Starting Flask documentation on port 5000..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
