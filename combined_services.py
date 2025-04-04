"""
This script starts both the FastAPI service and Flask application
for the MCP Assessor Agent API in a single workflow.
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("output.log")]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set environment variable for Flask-FastAPI communication
os.environ["FASTAPI_URL"] = "http://127.0.0.1:8000"
os.environ["FLASK_PORT"] = "5000"

# Global process references
fastapi_process = None
flask_process = None

def log_output(process, service_name):
    """Monitor and log process output."""
    for line in iter(process.stdout.readline, ""):
        if line:
            logger.info(f"{service_name}: {line.strip()}")

def start_fastapi():
    """Start the FastAPI application."""
    global fastapi_process
    
    logger.info("Starting FastAPI service on port 8000...")
    try:
        # Set environment variables that might be missing
        os.environ["FASTAPI_PORT"] = "8000"
        if "FASTAPI_URL" not in os.environ:
            os.environ["FASTAPI_URL"] = "http://0.0.0.0:8000"
        
        # Run FastAPI with uvicorn
        fastapi_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start thread to monitor output
        threading.Thread(target=log_output, args=(fastapi_process, "FastAPI"), daemon=True).start()
        
        # Wait for FastAPI to initialize
        time.sleep(5)
        
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
        # Start Flask with gunicorn
        flask_process = subprocess.Popen(
            ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start thread to monitor output
        threading.Thread(target=log_output, args=(flask_process, "Flask"), daemon=True).start()
        
        logger.info("Flask service started")
        return True
    except Exception as e:
        logger.error(f"Error starting Flask documentation: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Shutting down services...")
    
    if fastapi_process:
        try:
            fastapi_process.terminate()
            logger.info("Terminated FastAPI process")
        except Exception as e:
            logger.error(f"Error terminating FastAPI process: {e}")
    
    if flask_process:
        try:
            flask_process.terminate()
            logger.info("Terminated Flask process")
        except Exception as e:
            logger.error(f"Error terminating Flask process: {e}")
    
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("Starting MCP Assessor Agent API services...")
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        sys.exit(1)
    
    # Start Flask documentation
    if not start_flask():
        logger.error("Failed to start Flask documentation")
        cleanup()
        sys.exit(1)
    
    logger.info("All services started successfully")
    logger.info("Flask documentation available at http://localhost:5000")
    logger.info("FastAPI service available at http://localhost:8000")
    
    # Keep both services running
    try:
        while True:
            # Check if FastAPI is still running
            if fastapi_process and fastapi_process.poll() is not None:
                logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
                restart_fastapi = True
                if not start_fastapi():
                    logger.error("Failed to restart FastAPI service")
                    sys.exit(1)
            
            # Check if Flask is still running
            if flask_process and flask_process.poll() is not None:
                logger.error(f"Flask process exited with code {flask_process.returncode}")
                if not start_flask():
                    logger.error("Failed to restart Flask documentation")
                    sys.exit(1)
            
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup()

if __name__ == "__main__":
    main()