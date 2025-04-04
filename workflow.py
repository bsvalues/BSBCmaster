#!/usr/bin/env python3
"""
MCP Assessor Agent API - Workflow Manager

This script manages the startup of both FastAPI and Flask services for the MCP Assessor Agent API.
It handles environment configuration, process management, and logging.
"""

import os
import sys
import time
import signal
import subprocess
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("mcp_workflow")

# Load environment variables
load_dotenv()

# Configure service settings
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", 8000))
FASTAPI_URL = os.environ.get("FASTAPI_URL", f"http://localhost:{FASTAPI_PORT}")

# Store process information
processes = []

def start_fastapi():
    """Start the FastAPI service."""
    logger.info(f"Starting FastAPI service on port {FASTAPI_PORT}...")
    
    # Start the FastAPI process
    fastapi_cmd = ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(FASTAPI_PORT)]
    fastapi_process = subprocess.Popen(
        fastapi_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Add process to the list for later cleanup
    processes.append(("fastapi", fastapi_process))
    
    # Start the log reader in a background thread
    import threading
    
    def read_logs():
        """Read logs from FastAPI process."""
        if fastapi_process.stdout is None:
            logger.error("FastAPI process has no stdout")
            return
            
        for line in iter(fastapi_process.stdout.readline, ''):
            sys.stdout.write(f"FastAPI: {line}")
            sys.stdout.flush()
    
    # Start log reader in a separate thread
    log_thread = threading.Thread(target=read_logs, daemon=True)
    log_thread.start()
    
    # Wait for the service to start
    time.sleep(2)
    
    return fastapi_process

def wait_for_fastapi():
    """Wait for FastAPI service to be ready."""
    logger.info("Waiting for FastAPI service to initialize...")
    
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            # Try to reach the FastAPI service - use /health endpoint
            response = requests.get(f"{FASTAPI_URL}/health", timeout=1)
            if response.status_code == 200:
                logger.info(f"FastAPI service is ready (attempt {attempt}/{max_attempts})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Try with API prefix as an alternative
        try:
            response = requests.get(f"{FASTAPI_URL}/api/health", timeout=1)
            if response.status_code == 200:
                logger.info(f"FastAPI service is ready with API prefix (attempt {attempt}/{max_attempts})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_attempts:
            logger.info(f"Waiting for FastAPI to start (attempt {attempt}/{max_attempts})...")
            time.sleep(1)
    
    logger.warning(f"FastAPI service did not become ready after {max_attempts} attempts")
    return False

def start_flask():
    """Start the Flask service."""
    logger.info(f"Starting Flask documentation on port {FLASK_PORT}...")
    
    # Set FASTAPI_URL in the environment
    env = os.environ.copy()
    env["FASTAPI_URL"] = FASTAPI_URL
    
    # Start the Flask process
    flask_cmd = ["gunicorn", "--bind", f"0.0.0.0:{FLASK_PORT}", "--reuse-port", "--reload", "main:app"]
    flask_process = subprocess.Popen(
        flask_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Add process to the list for later cleanup
    processes.append(("flask", flask_process))
    
    # Return process for logging
    return flask_process

def log_flask_output(flask_process):
    """Log output from Flask process."""
    import threading
    
    def read_logs():
        """Read logs from Flask process."""
        if flask_process.stdout is None:
            logger.error("Flask process has no stdout")
            return
            
        for line in iter(flask_process.stdout.readline, ''):
            sys.stdout.write(f"Flask: {line}")
            sys.stdout.flush()
    
    # Start log reader in a separate thread
    log_thread = threading.Thread(target=read_logs, daemon=True)
    log_thread.start()
    
    return log_thread

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
        # Start FastAPI in a separate thread
        fastapi_process = start_fastapi()
        
        # Wait for FastAPI to initialize
        wait_for_fastapi()
        
        # Start Flask
        flask_process = start_flask()
        
        # Log Flask output
        log_flask_output(flask_process)
        
        # Keep the script running
        while all(p.poll() is None for _, p in processes):
            time.sleep(1)
        
        # If we get here, one of the processes has died
        for name, process in processes:
            if process.poll() is not None:
                logger.error(f"{name} process has exited with code {process.returncode}")
        
        # Clean up
        cleanup()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        cleanup()
    except Exception as e:
        logger.exception(f"Error in main process: {e}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()