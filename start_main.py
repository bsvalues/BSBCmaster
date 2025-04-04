"""
This script serves as the main entry point for the MCP Assessor Agent API.
It starts both Flask and FastAPI services using the workflow management system.
When run directly, it uses gunicorn to serve the Flask application and starts
the FastAPI application in a separate process.
"""

import os
import sys
import subprocess
import threading
import time
import signal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_starter")

# Global variables
processes = []
FLASK_PORT = 5000
FASTAPI_PORT = 8000
FASTAPI_URL = f"http://localhost:{FASTAPI_PORT}"

def start_fastapi():
    """Start the FastAPI service."""
    logger.info(f"Starting FastAPI service on port {FASTAPI_PORT}...")
    
    # Set FASTAPI_PORT in the environment
    env = os.environ.copy()
    
    # Start the FastAPI process using uvicorn
    fastapi_cmd = ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", str(FASTAPI_PORT)]
    fastapi_process = subprocess.Popen(
        fastapi_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Add process to the list for later cleanup
    processes.append(("fastapi", fastapi_process))
    
    # Start log reader thread
    def read_logs():
        """Read logs from FastAPI process."""
        if fastapi_process.stdout is None:
            logger.error("FastAPI process has no stdout")
            return
            
        for line in iter(fastapi_process.stdout.readline, ''):
            sys.stdout.write(f"FastAPI: {line}")
            sys.stdout.flush()
    
    log_thread = threading.Thread(target=read_logs, daemon=True)
    log_thread.start()
    
    return fastapi_process

def wait_for_fastapi():
    """Wait for FastAPI service to be ready."""
    import requests
    
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(f"{FASTAPI_URL}/health", timeout=1)
            if response.status_code == 200:
                logger.info(f"FastAPI service is ready (attempt {attempt}/{max_attempts})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Try with root health as an alternative
        try:
            response = requests.get(f"{FASTAPI_URL}/api/health", timeout=1)
            if response.status_code == 200:
                logger.info(f"FastAPI service is ready on API prefix endpoint (attempt {attempt}/{max_attempts})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_attempts:
            logger.info(f"Waiting for FastAPI to start (attempt {attempt}/{max_attempts})...")
            time.sleep(1)
    
    logger.warning(f"FastAPI service did not become ready after {max_attempts} attempts")
    return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up processes...")
    
    for name, process in processes:
        if process.poll() is None:  # Process is still running
            logger.info(f"Terminating {name} process (PID: {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} process did not terminate gracefully, killing...")
                process.kill()
    
    logger.info("Cleanup complete")
    sys.exit(0)

def main():
    """Main function to run both services."""
    logger.info("Starting MCP Assessor Agent API services...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start FastAPI
        logger.info("Starting FastAPI service...")
        fastapi_process = start_fastapi()
        
        # Wait for FastAPI to be ready before starting Flask
        logger.info("Waiting for FastAPI to be ready...")
        if not wait_for_fastapi():
            logger.warning("FastAPI service is not ready, continuing anyway")
        
        # In this case, we don't need to start Flask separately
        # as it will be started by the Replit workflow
        logger.info("Flask service will be started by the Replit workflow")
        
        # Keep the script running to maintain the FastAPI process
        while fastapi_process.poll() is None:
            time.sleep(1)
        
        # If we get here, the FastAPI process has died
        logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
        
        # Clean up
        cleanup()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        cleanup()
    except Exception as e:
        logger.exception(f"Error in main process: {e}")
        cleanup()
        sys.exit(1)

# Import Flask app if this is loaded by gunicorn
from app_setup import app

if __name__ == "__main__":
    main()