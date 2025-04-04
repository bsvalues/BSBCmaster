#!/usr/bin/env python3
"""
This script runs both Flask and FastAPI services in parallel,
ensuring environment variables are properly loaded from .env first.
"""

import os
import sys
import time
import subprocess
import signal
import threading
from dotenv import load_dotenv

# Global variables
processes = []

def run_flask():
    """Run the Flask application."""
    print("Starting Flask application on port 5000...")
    flask_cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
    flask_proc = subprocess.Popen(flask_cmd)
    processes.append(flask_proc)
    return flask_proc

def run_fastapi():
    """Run the FastAPI application."""
    print("Starting FastAPI application on port 8000...")
    fastapi_cmd = ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    fastapi_proc = subprocess.Popen(fastapi_cmd)
    processes.append(fastapi_proc)
    return fastapi_proc

def signal_handler(sig, frame):
    """Handle signals like SIGINT (Ctrl+C)."""
    print("\nShutting down services...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

def main():
    """Main function."""
    # Load environment variables from .env
    print("Loading environment variables from .env file...")
    load_dotenv()
    
    # Print loaded API key (masked for security)
    api_key = os.environ.get("API_KEY", "")
    if api_key:
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        print(f"API_KEY is loaded: {masked_key}")
    else:
        print("WARNING: API_KEY is not set in environment variables")
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start FastAPI
    fastapi_proc = run_fastapi()
    
    # Give FastAPI time to start
    time.sleep(2)
    
    # Start Flask
    flask_proc = run_flask()
    
    # Wait for the processes to complete
    try:
        flask_proc.wait()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()