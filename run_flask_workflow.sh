#!/bin/bash

# Export environment variables
export $(cat .env 2>/dev/null | grep -v '^#' | xargs)

# Run Flask service
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app