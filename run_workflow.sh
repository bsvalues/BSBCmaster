#!/bin/bash
# Start both FastAPI and Flask via gunicorn

# Start the combined_workflow.py script in the background to handle FastAPI
python combined_workflow.py &

# Then start gunicorn for Flask
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app