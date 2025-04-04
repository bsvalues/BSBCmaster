"""
MCP Assessor Agent API - Integrated Services Runner

This script starts both the Flask documentation interface and the FastAPI service
with proper coordination, error handling, and environment setup.
"""

import os
import sys
import signal
import subprocess
import threading
import time
import logging
import socket
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("integrated_services.log"),
    ]
)
logger = logging.getLogger(__name__)

# Global processes list for cleanup
processes = []
MAX_RETRY_ATTEMPTS = 3

def check_port_available(port):
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        result = True
    except:
        result = False
    finally:
        sock.close()
    return result

def wait_for_port(port, timeout=30):
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            socket.create_connection(('127.0.0.1', port), timeout=1)
            return True
        except:
            time.sleep(1)
    return False

def log_output(process, service_name):
    """Monitor and log process output."""
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.decode('utf-8').rstrip()
            logger.info(f"[{service_name}] {line}")
    
    # Check if process exited with an error
    if process.returncode != 0:
        logger.error(f"{service_name} exited with code {process.returncode}")

def start_fastapi():
    """Start the FastAPI application."""
    logger.info("Starting FastAPI service on port 8000...")
    
    # Check if port is already in use
    if not check_port_available(8000):
        logger.warning("Port 8000 is already in use. Attempting to free it...")
        try:
            subprocess.run(["pkill", "-f", "uvicorn.*:8000"], check=False)
            time.sleep(2)
            if not check_port_available(8000):
                logger.error("Could not free port 8000. Cannot start FastAPI service.")
                return False
        except Exception as e:
            logger.error(f"Error freeing port 8000: {str(e)}")
            return False
    
    # Set up environment
    env = os.environ.copy()
    
    # Run FastAPI using uvicorn with additional error capture
    fastapi_cmd = [
        "python", "-m", "uvicorn", "app:app", 
        "--host", "0.0.0.0", "--port", "8000", "--reload"
    ]
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            process = subprocess.Popen(
                fastapi_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=False,
                env=env
            )
            processes.append(process)
            
            # Record PID to file for potential external management
            with open("fastapi.pid", "w") as f:
                f.write(str(process.pid))
            
            # Start a thread to monitor and log output
            threading.Thread(
                target=log_output,
                args=(process, "FastAPI"),
                daemon=True
            ).start()
            
            # Wait for service to start
            logger.info("Waiting for FastAPI to initialize...")
            if not wait_for_port(8000, timeout=15):
                logger.error("Timed out waiting for FastAPI to start")
                process.terminate()
                retry_count += 1
                continue
            
            # Check if process is still running
            if process.poll() is not None:
                logger.error(f"FastAPI failed to start (exit code {process.returncode})")
                retry_count += 1
                continue
            
            logger.info("FastAPI service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting FastAPI (attempt {retry_count+1}): {str(e)}")
            retry_count += 1
            time.sleep(2)
    
    logger.error(f"Failed to start FastAPI after {MAX_RETRY_ATTEMPTS} attempts")
    return False

def start_flask():
    """Start the Flask documentation application."""
    logger.info("Starting Flask documentation on port 5000...")
    
    # Check if port is already in use
    if not check_port_available(5000):
        logger.warning("Port 5000 is already in use. Attempting to free it...")
        try:
            subprocess.run(["pkill", "-f", "gunicorn.*:5000"], check=False)
            time.sleep(2)
            if not check_port_available(5000):
                logger.error("Could not free port 5000. Cannot start Flask service.")
                return False
        except Exception as e:
            logger.error(f"Error freeing port 5000: {str(e)}")
            return False
    
    # Run Flask using gunicorn
    flask_cmd = [
        "gunicorn", "--bind", "0.0.0.0:5000", 
        "--access-logfile", "-", "--error-logfile", "-",
        "--reload", "main:app"
    ]
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            process = subprocess.Popen(
                flask_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=False
            )
            processes.append(process)
            
            # Start a thread to monitor and log output
            threading.Thread(
                target=log_output,
                args=(process, "Flask"),
                daemon=True
            ).start()
            
            # Wait for service to start
            logger.info("Waiting for Flask to initialize...")
            if not wait_for_port(5000, timeout=15):
                logger.error("Timed out waiting for Flask to start")
                process.terminate()
                retry_count += 1
                continue
            
            # Check if process is still running
            if process.poll() is not None:
                logger.error(f"Flask failed to start (exit code {process.returncode})")
                retry_count += 1
                continue
            
            logger.info("Flask documentation started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting Flask (attempt {retry_count+1}): {str(e)}")
            retry_count += 1
            time.sleep(2)
    
    logger.error(f"Failed to start Flask after {MAX_RETRY_ATTEMPTS} attempts")
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
    """Main function to run both services."""
    # Load environment variables
    load_dotenv()
    
    # Make sure required environments are set
    if not os.environ.get("API_KEY"):
        logger.warning("API_KEY not set. Setting default value for development.")
        os.environ["API_KEY"] = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    
    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("=" * 60)
    logger.info("Starting MCP Assessor Agent API integrated services...")
    logger.info("=" * 60)
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service. Exiting...")
        cleanup()
        return
    
    # Start Flask documentation
    if not start_flask():
        logger.error("Failed to start Flask documentation. Exiting...")
        cleanup()
        return
    
    logger.info("=" * 60)
    logger.info("All services started successfully")
    logger.info("FastAPI running on port 8000")
    logger.info("Flask documentation running on port 5000")
    logger.info("=" * 60)
    
    try:
        # Keep script running and monitor processes
        while True:
            time.sleep(2)
            
            # Check if any process has exited
            for process in processes:
                if process.poll() is not None:
                    service_name = "FastAPI" if "uvicorn" in str(process.args) else "Flask"
                    logger.error(f"{service_name} has exited unexpectedly with code {process.returncode}")
                    
                    # Attempt to restart the service
                    logger.info(f"Attempting to restart {service_name}...")
                    if service_name == "FastAPI":
                        if not start_fastapi():
                            logger.error("Failed to restart FastAPI service. Exiting...")
                            cleanup()
                            return
                    else:
                        if not start_flask():
                            logger.error("Failed to restart Flask service. Exiting...")
                            cleanup()
                            return
                    
                    # Remove the old process from the list
                    processes.remove(process)
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()

if __name__ == "__main__":
    main()