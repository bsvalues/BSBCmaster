"""
This script serves as the entry point for the Replit workflow.
It starts both the FastAPI service and the Flask application.
"""

import os
import signal
import subprocess
import sys
import threading
import time
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler
file_handler = RotatingFileHandler('workflow.log', maxBytes=10485760, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Global list for process management
processes = []

def log_output(process, service_name):
    """Monitor and log process output."""
    for line in iter(process.stdout.readline, b''):
        try:
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                logger.info(f"[{service_name}] {decoded_line}")
        except UnicodeDecodeError:
            logger.warning(f"[{service_name}] Could not decode output line")
        except Exception as e:
            logger.error(f"[{service_name}] Error processing output: {str(e)}")
    
    # Check if process exited with an error
    if process.poll() is not None and process.returncode != 0:
        logger.error(f"{service_name} exited with code {process.returncode}")

def start_fastapi():
    """Start the FastAPI application."""
    logger.info("Starting FastAPI service on port 8000...")
    # Start uvicorn with app module
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
    logger.info("Cleaning up processes...")
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
    
    logger.info("All processes stopped")
    sys.exit(0)

def main():
    """Main function to setup FastAPI before gunicorn starts Flask."""
    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("Starting MCP Assessor Agent API services...")
    
    # Start FastAPI first
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        # Don't exit, let Flask still start
    
    # The Flask app will be started by the Replit workflow (gunicorn)
    logger.info("FastAPI service is running, Flask will be started by gunicorn")
    
    # Keep the script running to maintain FastAPI
    try:
        # Wait for processes to complete or user interrupt
        while True:
            time.sleep(1)
            # Check if FastAPI process has exited
            for process in processes:
                if process.poll() is not None:
                    logger.error(f"FastAPI service has exited unexpectedly with code {process.returncode}")
                    # Restart FastAPI
                    logger.info("Attempting to restart FastAPI...")
                    processes.remove(process)
                    if not start_fastapi():
                        logger.error("Failed to restart FastAPI service")
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()

if __name__ == "__main__":
    main()