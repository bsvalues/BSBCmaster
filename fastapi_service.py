#!/usr/bin/env python3
"""
This script runs the FastAPI service using Gunicorn with uvicorn workers.
"""

import os
import sys
import time
import subprocess
import signal

# Global process variable
fastapi_proc = None

def run_fastapi():
    """Run the FastAPI application."""
    print("Starting FastAPI application on port 8000...")
    cmd = ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", 
           "--bind", "0.0.0.0:8000", "--reload", "asgi:app"]
    
    global fastapi_proc
    fastapi_proc = subprocess.Popen(cmd)
    return fastapi_proc

def signal_handler(sig, frame):
    """Handle signals like SIGINT (Ctrl+C)."""
    print("\nShutting down FastAPI service...")
    if fastapi_proc:
        fastapi_proc.terminate()
    sys.exit(0)

def main():
    """Main function."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start FastAPI
    proc = run_fastapi()
    
    # Wait for the process to complete
    try:
        proc.wait()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()