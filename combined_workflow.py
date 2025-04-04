"""
This script is a simplified version of run_dual_app.py specifically for the workflow.
It starts both the FastAPI service and Flask documentation.
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
        logging.FileHandler("workflow.log"),
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
    # Run FastAPI using uvicorn
    fastapi_cmd = [
        "python", "-m", "uvicorn", "app:app", 
        "--host", "0.0.0.0", "--port", "8000", "--reload"
    ]
    
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
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            logger.error(f"FastAPI failed to start (exit code {process.returncode})")
            return False
        
        logger.info("FastAPI service started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting FastAPI: {str(e)}")
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
    """Main function to start FastAPI before gunicorn starts Flask."""
    # Load environment variables
    load_dotenv()
    
    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("Starting MCP Assessor Agent API services...")
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        cleanup()
        
    logger.info("Waiting for Flask to start via gunicorn...")
    
    # In workflow, Flask will be started by gunicorn separately
    # We just need to keep this script running
    try:
        # Keep script running
        while True:
            time.sleep(1)
            # Check if any process has exited
            for process in processes:
                if process.poll() is not None:
                    logger.error(f"FastAPI has exited unexpectedly with code {process.returncode}")
                    cleanup()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()

if __name__ == "__main__":
    main()