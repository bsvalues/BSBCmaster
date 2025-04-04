"""
This script runs both the Flask and FastAPI applications in separate processes.
"""

import os
import logging
import subprocess
import threading
import signal
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global processes list for cleanup
processes = []

def run_process(command, name):
    """Run a process and add it to the global processes list."""
    logger.info(f"Starting {name} process: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    processes.append((process, name))
    
    # Start a thread to read and log the process output
    def log_output():
        for line in process.stdout:
            logger.info(f"[{name}] {line.strip()}")
    
    threading.Thread(target=log_output, daemon=True).start()
    return process

def start_flask():
    """Start the Flask application."""
    flask_port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting Flask documentation on port {flask_port}")
    return run_process(
        ["gunicorn", "--bind", f"0.0.0.0:{flask_port}", "--reload", "main:app"],
        "Flask"
    )

def start_fastapi():
    """Start the FastAPI application."""
    fastapi_port = int(os.environ.get("FASTAPI_PORT", 8000))
    logger.info(f"Starting FastAPI service on port {fastapi_port}")
    return run_process(
        ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", str(fastapi_port), "--reload"],
        "FastAPI"
    )

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Shutting down all processes...")
    for process, name in processes:
        try:
            logger.info(f"Terminating {name} process (PID: {process.pid})")
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"{name} process did not terminate gracefully, killing it")
            process.kill()
        except Exception as e:
            logger.error(f"Error terminating {name} process: {e}")
    
    logger.info("All processes terminated")
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Check if API_KEY is set
        api_key = os.environ.get("API_KEY")
        if not api_key:
            custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
            logger.warning(f"API_KEY not set. Using custom secure key: {custom_key[:8]}...")
            os.environ["API_KEY"] = custom_key
            
        # Start the services
        flask_process = start_flask()
        time.sleep(2)  # Give Flask a moment to start
        fastapi_process = start_fastapi()
        
        # Wait for processes to finish (they should run indefinitely)
        logger.info("All services started successfully")
        logger.info(f"Flask documentation available at http://localhost:{os.environ.get('FLASK_PORT', 5000)}")
        logger.info(f"FastAPI service available at http://localhost:{os.environ.get('FASTAPI_PORT', 8000)}")
        
        # Keep the main thread alive
        while all(p[0].poll() is None for p in processes):
            time.sleep(1)
        
        # If we get here, at least one process has exited
        for process, name in processes:
            if process.poll() is not None:
                logger.error(f"{name} process exited unexpectedly with code {process.poll()}")
        
        # Clean up remaining processes
        cleanup()
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        cleanup()

if __name__ == "__main__":
    main()