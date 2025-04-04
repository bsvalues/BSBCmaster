#!/bin/bash

# Export environment variables
export $(cat .env 2>/dev/null | grep -v '^#' | xargs)

# Run FastAPI service
python run_api.py