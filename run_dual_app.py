"""
MCP Assessor Agent API - Integrated Services Runner

This script starts both the Flask documentation interface (port 5000) and 
the FastAPI service (port 8000) with proper coordination and error handling.
"""

import os
import sys
import signal
import subprocess
import threading
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("output.log"),
    ]
)
logger = logging.getLogger(__name__)

# Global processes list for cleanup
processes = []

def log_output(process, service_name):
    """Monitor and log process output."""
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.decode('utf-8').rstrip()
            logger.info(f"[{service_name}] {line}")
    
    # Check if process exited with an error
    if process.returncode != 0:
        logger.error(f"{service_name} exited with code {process.returncode}")

def start_fastapi():
    """Start the FastAPI application."""
    logger.info("Starting FastAPI service on port 8000...")
    # Correctly import from app.py which imports the FastAPI app from the app package
    fastapi_cmd = [
        "python", "-m", "uvicorn", "app:app", 
        "--host", "0.0.0.0", "--port", "8000", "--reload"
    ]
    
    # Start the process
    try:
        process = subprocess.Popen(
            fastapi_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        processes.append(process)
        
        # Start a thread to monitor and log output
        threading.Thread(
            target=log_output,
            args=(process, "FastAPI"),
            daemon=True
        ).start()
        
        # Wait for service to start
        logger.info("Waiting for FastAPI to initialize...")
        time.sleep(5)  # Give more time for initialization
        
        # Check if process is still running
        if process.poll() is not None:
            logger.error(f"FastAPI failed to start (exit code {process.returncode})")
            return False
        
        logger.info("FastAPI service started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting FastAPI: {str(e)}")
        return False

def start_flask():
    """Start the Flask documentation application."""
    logger.info("Starting Flask documentation on port 5000...")
    flask_cmd = [
        "gunicorn", "--bind", "0.0.0.0:5000", 
        "--reuse-port", "--reload", "main:app"
    ]
    
    # Start the process
    try:
        process = subprocess.Popen(
            flask_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        processes.append(process)
        
        # Start a thread to monitor and log output
        threading.Thread(
            target=log_output,
            args=(process, "Flask"),
            daemon=True
        ).start()
        
        # Wait for service to start
        logger.info("Waiting for Flask to initialize...")
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            logger.error(f"Flask failed to start (exit code {process.returncode})")
            return False
        
        logger.info("Flask documentation started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting Flask: {str(e)}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up services...")
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
    
    logger.info("All services stopped")
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Load environment variables
    load_dotenv()
    
    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("Starting MCP Assessor Agent API services...")
    
    try:
        # Start FastAPI first
        if not start_fastapi():
            logger.error("Failed to start FastAPI service, exiting")
            cleanup()
        
        # Then start Flask 
        if not start_flask():
            logger.error("Failed to start Flask documentation, exiting")
            cleanup()
        
        logger.info("Both services are now running")
        
        # Wait for processes to complete
        while True:
            time.sleep(1)
            # Check if any process has exited
            for process in processes:
                if process.poll() is not None:
                    logger.error(f"A service has exited unexpectedly with code {process.returncode}")
                    cleanup()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()

if __name__ == "__main__":
    main()