#!/bin/bash
# Run the workflow Python script first to start FastAPI
python workflow.py &
# Wait a bit to allow FastAPI to initialize
sleep 5
# Start Flask with gunicorn
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
