"""
Run both FastAPI and Flask services in a single process.
This script starts FastAPI in the background and then runs the Flask app.
"""

import os
import subprocess
import threading
import time
import signal
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global variable to track processes
fastapi_process = None

def log_output(process, prefix):
    """Log subprocess output with a prefix."""
    for line in iter(process.stdout.readline, ''):
        if line:
            logger.info(f"[{prefix}] {line.strip()}")

def start_fastapi():
    """Start the FastAPI service as a background process."""
    logger.info("Starting FastAPI service on port 8000")
    global fastapi_process
    try:
        fastapi_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start a thread to log the output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        # Wait a bit for FastAPI to start
        time.sleep(3)
        
        # Check if process is still running
        if fastapi_process.poll() is not None:
            logger.error(f"FastAPI process failed to start! Exit code: {fastapi_process.returncode}")
            return False
            
        logger.info("FastAPI service started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up resources on exit."""
    logger.info("Cleaning up processes")
    global fastapi_process
    
    if fastapi_process:
        logger.info("Terminating FastAPI process")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process didn't terminate gracefully, killing it")
            fastapi_process.kill()
    
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service, exiting")
        sys.exit(1)
    
    # Run Flask service with Gunicorn (this will block until it exits)
    logger.info("Starting Flask service on port 5000")
    try:
        # Use os.execvp to replace the current process with Gunicorn
        # This way, when Gunicorn receives signals, they'll be properly handled
        os.execvp("gunicorn", ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"])
    except OSError as e:
        logger.error(f"Failed to start Flask service: {e}")
        cleanup()

if __name__ == "__main__":
    main()