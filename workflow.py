"""
MCP Assessor Agent API - Replit Workflow

This script handles starting both the Flask documentation interface and the FastAPI service
with proper coordination, specifically designed for Replit's workflow environment.
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

# Global processes
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

def start_fastapi():
    """Start the FastAPI application."""
    logger.info("Starting FastAPI service on port 8000...")
    
    try:
        # Run FastAPI using uvicorn with reload for development
        fastapi_cmd = [
            "python", "-m", "uvicorn", "app:app", 
            "--host", "0.0.0.0", "--port", "8000", "--reload"
        ]
        
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
        
        # Wait for FastAPI to start
        time.sleep(3)
        
        return True
        
    except Exception as e:
        logger.error(f"Error starting FastAPI: {str(e)}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up services...")
    for process in processes:
        try:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
    
    logger.info("All services stopped")
    if signum is not None:
        sys.exit(0)

def main():
    """Main function to start FastAPI before gunicorn starts Flask."""
    # Load environment variables
    load_dotenv()
    
    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("=" * 60)
    logger.info("Starting MCP Assessor Agent API services...")
    logger.info("=" * 60)
    
    # Start FastAPI service in background
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        return
    
    logger.info("FastAPI service started successfully on port 8000")
    logger.info("Waiting for Replit workflow to start Flask documentation...")
    
    # Keep the script running until interrupted
    try:
        while True:
            time.sleep(2)
            
            # Check if FastAPI process has exited
            for process in processes:
                if process.poll() is not None:
                    logger.error(f"FastAPI has exited unexpectedly with code {process.returncode}")
                    if not start_fastapi():
                        logger.error("Failed to restart FastAPI service")
                        return
                    processes.remove(process)
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()

if __name__ == "__main__":
    main()