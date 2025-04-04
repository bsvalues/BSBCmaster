"""
MCP Assessor Agent API - Universal Service Starter

This script starts both the Flask documentation interface and FastAPI service 
in a way that works reliably with Replit's workflow system.
"""

import os
import sys
import subprocess
import time
import signal
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('both_services.log')
    ]
)
logger = logging.getLogger(__name__)

# Global variables to store process handles
fastapi_process = None
flask_process = None

def log_output(process, name):
    """Log output from a process."""
    for line in iter(process.stdout.readline, ''):
        try:
            # Check if the line is bytes or string
            if isinstance(line, bytes):
                decoded_line = line.decode('utf-8').rstrip()
            else:
                decoded_line = line.rstrip()
            
            logger.info(f"[{name}] {decoded_line}")
        except Exception as e:
            logger.error(f"Error logging output from {name}: {e}")

def start_fastapi():
    """Start the FastAPI service."""
    global fastapi_process
    
    try:
        # First check if port 8000 is in use and terminate the process if it is
        try:
            subprocess.run(
                ["fuser", "-k", "8000/tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Killed existing process on port 8000")
        except Exception:
            pass  # It's okay if this fails
        
        # Start the FastAPI service with explicit reload flag for development
        cmd = ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        logger.info(f"Starting FastAPI process with command: {' '.join(cmd)}")
        
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start a thread to log output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        logger.info("FastAPI process started")
        return True
    except Exception as e:
        logger.error(f"Error starting FastAPI: {e}")
        return False

def start_flask():
    """Start the Flask documentation service."""
    global flask_process
    
    try:
        # First check if port 5000 is in use and terminate the process if it is
        try:
            subprocess.run(
                ["fuser", "-k", "5000/tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Killed existing process on port 5000")
        except Exception:
            pass  # It's okay if this fails
        
        # Choose how to start the Flask service - using gunicorn for production
        cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
        logger.info(f"Starting Flask process with command: {' '.join(cmd)}")
        
        flask_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start a thread to log output
        threading.Thread(
            target=log_output,
            args=(flask_process, "Flask"),
            daemon=True
        ).start()
        
        logger.info("Flask process started")
        return True
    except Exception as e:
        logger.error(f"Error starting Flask: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up processes...")
    
    try:
        # Terminate FastAPI process
        if fastapi_process:
            logger.info("Terminating FastAPI process")
            fastapi_process.terminate()
            fastapi_process.wait(timeout=5)
            logger.info("FastAPI process terminated")
    except Exception as e:
        logger.error(f"Error terminating FastAPI process: {e}")
    
    try:
        # Terminate Flask process
        if flask_process:
            logger.info("Terminating Flask process")
            flask_process.terminate()
            flask_process.wait(timeout=5)
            logger.info("Flask process terminated")
    except Exception as e:
        logger.error(f"Error terminating Flask process: {e}")
    
    # Always exit with success unless explicitly specified
    sys.exit(0)

def check_service_health(port, max_attempts=30):
    """Check if a service is healthy."""
    import requests
    
    logger.info(f"Checking service health on port {port}")
    for i in range(max_attempts):
        try:
            response = requests.get(f"http://localhost:{port}/health")
            if response.status_code == 200:
                logger.info(f"Service on port {port} is healthy")
                return True
        except requests.RequestException:
            pass
        
        # Wait before trying again
        time.sleep(1)
    
    logger.warning(f"Service on port {port} did not become healthy after {max_attempts} attempts")
    return False

def main():
    """Main function to run both services."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start FastAPI first (background service)
        if not start_fastapi():
            logger.error("Failed to start FastAPI service")
            return 1
        
        # Wait a moment for FastAPI to initialize
        time.sleep(3)
        
        # Start the Flask application (documentation front-end)
        if not start_flask():
            logger.error("Failed to start Flask service")
            cleanup()
            return 1
        
        # Check health of both services
        flask_healthy = check_service_health(5000)
        fastapi_healthy = check_service_health(8000)
        
        if not flask_healthy:
            logger.warning("Flask service not responding to health checks")
        
        if not fastapi_healthy:
            logger.warning("FastAPI service not responding to health checks")
        
        # Keep the main thread alive to manage the processes
        logger.info("Both services started. Press Ctrl+C to exit.")
        
        # Block the main thread but allow for graceful shutdown
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if fastapi_process and fastapi_process.poll() is not None:
                logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
                break
            
            if flask_process and flask_process.poll() is not None:
                logger.error(f"Flask process exited with code {flask_process.returncode}")
                break
        
        # Something went wrong, clean up
        logger.info("One of the services exited unexpectedly, cleaning up...")
        cleanup()
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        cleanup()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)