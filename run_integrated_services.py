"""
MCP Assessor Agent API - Integrated Services Runner

This script starts both the Flask documentation interface and the FastAPI service
with proper coordination, error handling, and environment setup.
"""

import os
import sys
import subprocess
import time
import signal
import threading
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_services.log')
    ]
)
logger = logging.getLogger(__name__)

# Global variables to store process handles
fastapi_process = None
flask_process = None

def check_port_available(port):
    """Check if a port is available."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    available = True
    try:
        sock.bind(('0.0.0.0', port))
    except socket.error:
        available = False
    finally:
        sock.close()
    return available

def wait_for_port(port, timeout=30):
    """Wait for a port to become available."""
    logger.info(f"Waiting for port {port} to become available...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_port_available(port):
            logger.info(f"Port {port} is now available")
            return True
        time.sleep(1)
    logger.warning(f"Timed out waiting for port {port} to become available")
    return False

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
        # First make sure port 8000 is available
        if not check_port_available(8000):
            # Try to kill any process using port 8000
            try:
                subprocess.run(
                    ["fuser", "-k", "8000/tcp"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                logger.info("Killed existing process on port 8000")
                # Wait for port to become available
                if not wait_for_port(8000, timeout=10):
                    logger.error("Failed to free up port 8000")
                    return False
            except Exception as e:
                logger.error(f"Error stopping service on port 8000: {str(e)}")
                return False
        
        # Start FastAPI service
        cmd = ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        logger.info(f"Starting FastAPI service: {' '.join(cmd)}")
        
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        # Start a thread to log output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        # Wait for FastAPI to start
        logger.info("Waiting for FastAPI service to initialize...")
        time.sleep(5)
        
        # Check if service started successfully
        for _ in range(30):
            try:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    logger.info("FastAPI service is healthy")
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)
            
        logger.warning("FastAPI service did not respond to health check")
        return fastapi_process.poll() is None  # Return True if process is still running
    
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {str(e)}")
        return False

def start_flask():
    """Start the Flask documentation application."""
    global flask_process
    
    try:
        # First make sure port 5000 is available
        if not check_port_available(5000):
            # Try to kill any process using port 5000
            try:
                subprocess.run(
                    ["fuser", "-k", "5000/tcp"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                logger.info("Killed existing process on port 5000")
                # Wait for port to become available
                if not wait_for_port(5000, timeout=10):
                    logger.error("Failed to free up port 5000")
                    return False
            except Exception as e:
                logger.error(f"Error stopping service on port 5000: {str(e)}")
                return False
        
        # Start Flask service
        cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
        logger.info(f"Starting Flask service: {' '.join(cmd)}")
        
        flask_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        # Start a thread to log output
        threading.Thread(
            target=log_output,
            args=(flask_process, "Flask"),
            daemon=True
        ).start()
        
        # Wait for Flask to start
        logger.info("Waiting for Flask service to initialize...")
        time.sleep(5)
        
        # Check if service started successfully
        for _ in range(30):
            try:
                response = requests.get("http://localhost:5000/health", timeout=2)
                if response.status_code == 200:
                    logger.info("Flask service is healthy")
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)
            
        logger.warning("Flask service did not respond to health check")
        return flask_process.poll() is None  # Return True if process is still running
    
    except Exception as e:
        logger.error(f"Error starting Flask service: {str(e)}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up processes...")
    
    try:
        # Terminate FastAPI process
        if fastapi_process and fastapi_process.poll() is None:
            logger.info("Terminating FastAPI process")
            fastapi_process.terminate()
            try:
                fastapi_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FastAPI process did not terminate, killing it")
                fastapi_process.kill()
            logger.info("FastAPI process terminated")
    except Exception as e:
        logger.error(f"Error terminating FastAPI process: {str(e)}")
    
    try:
        # Terminate Flask process
        if flask_process and flask_process.poll() is None:
            logger.info("Terminating Flask process")
            flask_process.terminate()
            try:
                flask_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Flask process did not terminate, killing it")
                flask_process.kill()
            logger.info("Flask process terminated")
    except Exception as e:
        logger.error(f"Error terminating Flask process: {str(e)}")
    
    # Exit gracefully
    if signum is not None:
        sys.exit(0)

def main():
    """Main function to run both services."""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("=" * 80)
    logger.info("Starting MCP Assessor Agent API services")
    logger.info("=" * 80)
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        return 1
    
    logger.info("FastAPI service started successfully")
    
    # Start Flask service
    if not start_flask():
        logger.error("Failed to start Flask service")
        cleanup()
        return 1
    
    logger.info("Flask service started successfully")
    logger.info("Both services are now running.")
    logger.info("Flask Documentation: http://localhost:5000")
    logger.info("FastAPI Service: http://localhost:8000")
    
    # Monitor services
    try:
        while True:
            # Check if processes are still running
            fastapi_running = fastapi_process and fastapi_process.poll() is None
            flask_running = flask_process and flask_process.poll() is None
            
            if not fastapi_running:
                if fastapi_process:
                    logger.error(f"FastAPI process exited with code {fastapi_process.returncode}")
                logger.info("Attempting to restart FastAPI service...")
                if not start_fastapi():
                    logger.error("Failed to restart FastAPI service")
                    cleanup()
                    return 1
            
            if not flask_running:
                if flask_process:
                    logger.error(f"Flask process exited with code {flask_process.returncode}")
                logger.info("Attempting to restart Flask service...")
                if not start_flask():
                    logger.error("Failed to restart Flask service")
                    cleanup()
                    return 1
            
            # Sleep for a while before checking again
            time.sleep(5)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())