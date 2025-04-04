"""
This script runs the FastAPI service as a background process,
making it available for the Flask application to connect to.
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

# Global process reference
fastapi_process = None

def log_output(process, prefix):
    """Monitor and log process output."""
    for line in iter(process.stdout.readline, ""):
        if line:
            logger.info(f"{prefix}: {line.strip()}")

def start_fastapi():
    """Start the FastAPI service."""
    global fastapi_process
    
    logger.info("Starting FastAPI service on port 8000...")
    try:
        # Run FastAPI with uvicorn
        fastapi_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000"],
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

def cleanup(signum=None, frame=None):
    """Clean up resources on exit."""
    logger.info("Shutting down FastAPI service...")
    
    if fastapi_process:
        try:
            fastapi_process.terminate()
            logger.info("Terminated FastAPI process")
        except Exception as e:
            logger.error(f"Error terminating FastAPI process: {e}")
    
    sys.exit(0)

def main():
    """Main function."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        return
    
    try:
        # Keep script running
        while True:
            # Check if FastAPI is still running
            if fastapi_process.poll() is not None:
                logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
                break
            
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup()

if __name__ == "__main__":
    main()