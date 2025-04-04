"""
MCP Assessor Agent API - Combined Server Launcher

This script starts both the Flask documentation interface and FastAPI service
using Python's built-in subprocess module. It's designed for use with Replit
workflows.
"""

import os
import sys
import subprocess
import threading
import time
import signal
import logging
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("servers.log"),
    ]
)
logger = logging.getLogger(__name__)

# Global variables
processes = []

def handle_exit(signum=None, frame=None):
    """Handle exit signals and clean up processes."""
    logger.info("Exit handler triggered - stopping all servers")
    stop_all_processes()
    sys.exit(0)

def stop_all_processes():
    """Stop all running processes."""
    global processes
    
    for process in processes:
        try:
            if process and process.poll() is None:
                logger.info(f"Terminating process with PID {process.pid}")
                process.terminate()
                process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
    
    # Clear the processes list
    processes = []

def capture_output(process, name):
    """Capture and log output from a process."""
    while process and process.poll() is None:
        try:
            line = process.stdout.readline()
            if line:
                logger.info(f"[{name}] {line.decode('utf-8').strip()}")
        except Exception as e:
            logger.error(f"Error reading output from {name}: {e}")
            break

def start_fastapi():
    """Start the FastAPI service."""
    try:
        logger.info("Starting FastAPI service on port 8000...")
        cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
        
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        logger.info(f"FastAPI started with PID {fastapi_process.pid}")
        processes.append(fastapi_process)
        
        # Start thread to capture output
        output_thread = threading.Thread(
            target=capture_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        )
        output_thread.start()
        
        return fastapi_process
    except Exception as e:
        logger.error(f"Error starting FastAPI: {e}")
        return None

def start_flask():
    """Start the Flask documentation service."""
    try:
        logger.info("Starting Flask documentation on port 5000...")
        cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "main:app"]
        
        flask_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        logger.info(f"Flask started with PID {flask_process.pid}")
        processes.append(flask_process)
        
        # Start thread to capture output
        output_thread = threading.Thread(
            target=capture_output,
            args=(flask_process, "Flask"),
            daemon=True
        )
        output_thread.start()
        
        return flask_process
    except Exception as e:
        logger.error(f"Error starting Flask: {e}")
        return None

def check_service_health(process, name, port, max_attempts=30):
    """Check if a service is healthy by making HTTP requests."""
    import urllib.request
    
    base_url = f"http://localhost:{port}"
    endpoint = "/health" if name == "FastAPI" else "/"
    url = base_url + endpoint
    
    logger.info(f"Checking {name} health at {url}")
    
    for attempt in range(max_attempts):
        if process and process.poll() is not None:
            logger.error(f"{name} process terminated with code {process.returncode}")
            return False
            
        try:
            response = urllib.request.urlopen(url, timeout=1)
            if response.status == 200:
                logger.info(f"{name} is healthy (status 200)")
                return True
        except Exception as e:
            logger.debug(f"Health check attempt {attempt+1}/{max_attempts} failed: {e}")
        
        time.sleep(1)
    
    logger.error(f"{name} failed to become healthy after {max_attempts} attempts")
    return False

def main():
    """Main function."""
    logger.info("Starting MCP Assessor Agent API services")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Start FastAPI first
        fastapi_process = start_fastapi()
        if not fastapi_process:
            logger.error("Failed to start FastAPI service")
        
        # Start Flask
        flask_process = start_flask()
        if not flask_process:
            logger.error("Failed to start Flask service")
        
        # Check health of both services
        fastapi_healthy = check_service_health(fastapi_process, "FastAPI", 8000)
        flask_healthy = check_service_health(flask_process, "Flask", 5000)
        
        if fastapi_healthy and flask_healthy:
            logger.info("Both services are running and healthy")
            logger.info("- Flask documentation: http://localhost:5000")
            logger.info("- FastAPI service: http://localhost:8000")
        else:
            if not fastapi_healthy:
                logger.error("FastAPI service is not healthy")
            if not flask_healthy:
                logger.error("Flask service is not healthy")
        
        # Keep the script running to maintain the subprocesses
        while True:
            # Check if processes are still running
            if fastapi_process and fastapi_process.poll() is not None:
                logger.error(f"FastAPI terminated unexpectedly with code {fastapi_process.returncode}")
                # Restart FastAPI if it crashes
                fastapi_process = start_fastapi()
            
            if flask_process and flask_process.poll() is not None:
                logger.error(f"Flask terminated unexpectedly with code {flask_process.returncode}")
                # Restart Flask if it crashes
                flask_process = start_flask()
            
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        stop_all_processes()
        logger.info("All services stopped")

if __name__ == "__main__":
    main()