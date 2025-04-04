"""
Combined runner for both FastAPI and Flask applications with improved error handling.
This script starts both services and monitors their operation.
"""

import os
import sys
import time
import signal
import threading
import subprocess
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("output.log"),
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global process references
fastapi_process = None
flask_process = None

def log_output(process, service_name):
    """Monitor and log process output."""
    for line in iter(process.stdout.readline, ''):
        if line:
            logger.info(f"{service_name}: {line.strip()}")

def start_fastapi():
    """Start the FastAPI application."""
    global fastapi_process
    
    logger.info("Starting FastAPI service on port 8000...")
    try:
        # Use subprocess to run the FastAPI service
        fastapi_process = subprocess.Popen(
            [sys.executable, "run_api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start thread to monitor output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        logger.info("FastAPI service started")
        return True
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return False

def start_flask():
    """Start the Flask application."""
    global flask_process
    
    logger.info("Starting Flask documentation on port 5000...")
    try:
        # Use subprocess to run gunicorn for Flask
        flask_process = subprocess.Popen(
            ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start thread to monitor output
        threading.Thread(
            target=log_output,
            args=(flask_process, "Flask"),
            daemon=True
        ).start()
        
        logger.info("Flask service started")
        return True
    except Exception as e:
        logger.error(f"Error starting Flask service: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Shutting down services...")
    
    if fastapi_process:
        logger.info("Terminating FastAPI process...")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process did not terminate gracefully, forcing...")
            fastapi_process.kill()
    
    if flask_process:
        logger.info("Terminating Flask process...")
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Flask process did not terminate gracefully, forcing...")
            flask_process.kill()
    
    logger.info("All services stopped")
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("Starting MCP Assessor Agent API services...")
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        cleanup()
        return
    
    # Wait for FastAPI to initialize
    logger.info("Waiting for FastAPI to initialize...")
    time.sleep(5)
    
    # Start Flask service
    if not start_flask():
        logger.error("Failed to start Flask service")
        cleanup()
        return
    
    # Monitor services
    try:
        while True:
            # Check if processes are still running
            if fastapi_process.poll() is not None:
                logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
                cleanup()
                return
            
            if flask_process.poll() is not None:
                logger.error(f"Flask process exited with code {flask_process.returncode}")
                cleanup()
                return
            
            # Wait before checking again
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup()

if __name__ == "__main__":
    main()