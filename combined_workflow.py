"""
This script is a simplified version of run_dual_app.py specifically for the workflow.
It starts both the FastAPI service and Flask documentation.
"""

import os
import sys
import subprocess
import signal
import time
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("workflow.log")
    ]
)
logger = logging.getLogger(__name__)

# Global variables to store processes
fastapi_process = None

def log_output(process, service_name):
    """Monitor and log process output."""
    for line in iter(process.stdout.readline, b''):
        try:
            decoded_line = line.decode('utf-8').rstrip()
            logger.info(f"[{service_name}] {decoded_line}")
        except Exception as e:
            logger.error(f"Error logging output from {service_name}: {str(e)}")

def start_fastapi():
    """Start the FastAPI application."""
    global fastapi_process
    
    try:
        # Kill any existing processes on port 8000
        try:
            subprocess.run(
                ["fuser", "-k", "8000/tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Killed existing process on port 8000")
        except Exception:
            pass
        
        # Start FastAPI service using uvicorn
        cmd = ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        logger.info(f"Starting FastAPI service: {' '.join(cmd)}")
        
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        # Start a thread to monitor and log FastAPI output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        # Wait for FastAPI to initialize (this will be cut short when gunicorn starts)
        logger.info("FastAPI service starting. Continuing with Flask startup...")
        return True
    
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up processes...")
    
    if fastapi_process and fastapi_process.poll() is None:
        logger.info("Terminating FastAPI process")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process did not terminate, killing it")
            fastapi_process.kill()
    
    # Exit gracefully if called as a signal handler
    if signum is not None:
        sys.exit(0)

def main():
    """Main function to start FastAPI before gunicorn starts Flask."""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start FastAPI service in the background
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        return 1
    
    # The workflow will start gunicorn (Flask) automatically after this script
    # So we just need to keep this script running
    try:
        # Monitor the FastAPI process
        while fastapi_process and fastapi_process.poll() is None:
            time.sleep(1)
        
        # If we get here, FastAPI process has exited
        if fastapi_process:
            logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
            return fastapi_process.returncode
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())