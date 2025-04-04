"""
Combined runner script for both FastAPI and Flask applications.
This script starts both services and manages them using Python's multiprocessing.
"""

import os
import sys
import time
import signal
import multiprocessing
import subprocess
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_fastapi():
    """Start the FastAPI application using uvicorn."""
    logger.info("Starting FastAPI service on port 8000...")
    try:
        # Use subprocess to run uvicorn with the correct module path
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor and log uvicorn output
        for line in process.stdout:
            logger.info(f"FastAPI: {line.strip()}")
            
        # If we get here, the process has ended
        return_code = process.wait()
        logger.error(f"FastAPI process exited with code {return_code}")
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")

def run_flask():
    """Start the Flask application using gunicorn."""
    logger.info("Starting Flask documentation on port 5000...")
    try:
        # Use subprocess to run gunicorn
        process = subprocess.Popen(
            ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor and log gunicorn output
        for line in process.stdout:
            logger.info(f"Flask: {line.strip()}")
            
        # If we get here, the process has ended
        return_code = process.wait()
        logger.error(f"Flask process exited with code {return_code}")
    except Exception as e:
        logger.error(f"Error starting Flask service: {e}")

def main():
    """Main function to run both services."""
    logger.info("Starting both services...")
    
    # Create processes for both services
    fastapi_process = multiprocessing.Process(target=run_fastapi)
    flask_process = multiprocessing.Process(target=run_flask)
    
    # Register signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping services...")
        fastapi_process.terminate()
        flask_process.terminate()
        fastapi_process.join()
        flask_process.join()
        logger.info("All services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start processes
    fastapi_process.start()
    flask_process.start()
    
    logger.info(f"FastAPI started with PID {fastapi_process.pid}")
    logger.info(f"Flask started with PID {flask_process.pid}")
    
    # Give FastAPI a moment to start
    time.sleep(3)
    
    # Check if services started successfully
    if not fastapi_process.is_alive():
        logger.error("FastAPI service failed to start!")
    if not flask_process.is_alive():
        logger.error("Flask service failed to start!")
    
    try:
        # Keep the main process alive
        while fastapi_process.is_alive() and flask_process.is_alive():
            time.sleep(1)
        
        # If we get here, one of the processes has died
        logger.error("One of the services stopped unexpectedly!")
        
        if not fastapi_process.is_alive():
            logger.error("FastAPI service is no longer running")
        if not flask_process.is_alive():
            logger.error("Flask service is no longer running")
        
        # Terminate any remaining processes
        if fastapi_process.is_alive():
            fastapi_process.terminate()
        if flask_process.is_alive():
            flask_process.terminate()
            
    except KeyboardInterrupt:
        # Handle Ctrl+C
        logger.info("Keyboard interrupt received, stopping services...")
        fastapi_process.terminate()
        flask_process.terminate()
    
    # Wait for processes to complete
    fastapi_process.join()
    flask_process.join()
    
    logger.info("All services stopped")

if __name__ == "__main__":
    main()