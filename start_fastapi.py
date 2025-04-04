"""
This script starts the FastAPI service independently.

It's designed to be run separately from the Flask service, which is handled by the workflow.
"""

import os
import sys
import subprocess
import signal
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fastapi.log")
    ]
)
logger = logging.getLogger(__name__)

# Global variable for the process
fastapi_process = None

def signal_handler(signum, frame):
    """Handle signals like SIGINT (Ctrl+C) and SIGTERM."""
    logger.info(f"Received signal {signum}, shutting down...")
    if fastapi_process:
        logger.info("Terminating FastAPI process...")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
            logger.info("FastAPI process terminated successfully")
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process did not terminate, killing it")
            fastapi_process.kill()
    sys.exit(0)

def main():
    """Main function to start the FastAPI service."""
    global fastapi_process
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # First, check if port 8000 is already in use
    try:
        subprocess.run(
            ["fuser", "-k", "8000/tcp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        logger.info("Killed existing process on port 8000")
    except Exception:
        pass  # It's fine if this fails
    
    try:
        # Start FastAPI with uvicorn
        logger.info("Starting FastAPI service on port 8000...")
        
        cmd = ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        fastapi_process = subprocess.Popen(cmd)
        
        logger.info("FastAPI service started. Press Ctrl+C to exit.")
        
        # Keep the script running
        while fastapi_process.poll() is None:
            time.sleep(1)
        
        return_code = fastapi_process.returncode
        logger.info(f"FastAPI process exited with code {return_code}")
        return return_code
    
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())