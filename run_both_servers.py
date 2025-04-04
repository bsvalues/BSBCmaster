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
import socket
import urllib.request
from typing import Optional, List, Dict, Any
from datetime import datetime

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
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", 8000))

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
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {process.pid} did not terminate after 5 seconds, forcing...")
                    process.kill()
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
    
    # Clear the processes list
    processes = []

def capture_output(process, name):
    """Capture and log output from a process."""
    if not process:
        return
        
    log_file = f"{name.lower()}.log"
    
    with open(log_file, "wb") as f:
        while process and process.poll() is None:
            try:
                line = process.stdout.readline()
                if line:
                    # Write to log file
                    f.write(line)
                    f.flush()
                    
                    # Also log to console with prefix
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if line_str:
                        logger.info(f"[{name}] {line_str}")
            except Exception as e:
                logger.error(f"Error reading output from {name}: {e}")
                break

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """Kill any process using the specified port."""
    try:
        if os.name == 'posix':  # Linux/Mac
            output = subprocess.check_output(f"lsof -i :{port} -t", shell=True).decode().strip()
            if output:
                pid = int(output.split('\n')[0])
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Killed process {pid} that was using port {port}")
                time.sleep(1)  # Give the OS time to free the port
        else:  # Windows
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            if output:
                pid = int(output.split()[-1])
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Killed process {pid} that was using port {port}")
                time.sleep(1)  # Give the OS time to free the port
    except Exception as e:
        logger.warning(f"Failed to kill process on port {port}: {e}")

def ensure_port_available(port):
    """Ensure the specified port is available."""
    if is_port_in_use(port):
        logger.warning(f"Port {port} is already in use. Attempting to free it...")
        kill_process_on_port(port)
        
        # Double-check the port is now available
        if is_port_in_use(port):
            logger.error(f"Port {port} is still in use after attempted cleanup")
            return False
    return True

def start_fastapi():
    """Start the FastAPI service."""
    if not ensure_port_available(FASTAPI_PORT):
        return None
        
    try:
        logger.info(f"Starting FastAPI service on port {FASTAPI_PORT}...")
        
        # Use python module approach which is more reliable
        cmd = [
            sys.executable, 
            "-m", 
            "uvicorn", 
            "app:app", 
            "--host", 
            "0.0.0.0", 
            "--port", 
            str(FASTAPI_PORT), 
            "--log-level", 
            "info"
        ]
        
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
        
        # Give it a moment to start
        time.sleep(2)
        
        return fastapi_process
    except Exception as e:
        logger.error(f"Error starting FastAPI: {e}")
        return None

def start_flask():
    """Start the Flask documentation service."""
    if not ensure_port_available(FLASK_PORT):
        return None
        
    try:
        logger.info(f"Starting Flask documentation on port {FLASK_PORT}...")
        
        # Use gunicorn for production-grade serving
        cmd = [
            "gunicorn", 
            "--bind", 
            f"0.0.0.0:{FLASK_PORT}", 
            "--workers", 
            "1", 
            "--timeout", 
            "120", 
            "--access-logfile", 
            "-", 
            "main:app"
        ]
        
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
        
        # Give it a moment to start
        time.sleep(2)
        
        return flask_process
    except Exception as e:
        logger.error(f"Error starting Flask: {e}")
        return None

def check_service_health(process, name, port, max_attempts=30, retry_interval=1):
    """Check if a service is healthy by making HTTP requests."""
    if not process:
        logger.error(f"{name} process not started")
        return False
        
    base_url = f"http://localhost:{port}"
    endpoint = "/health" if name == "FastAPI" else "/"
    url = base_url + endpoint
    
    logger.info(f"Checking {name} health at {url}")
    
    for attempt in range(max_attempts):
        if process.poll() is not None:
            logger.error(f"{name} process terminated with code {process.returncode}")
            return False
            
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.status == 200:
                logger.info(f"{name} is healthy (status 200)")
                return True
        except Exception as e:
            if attempt % 5 == 0:  # Log only every 5th attempt to reduce noise
                logger.debug(f"Health check attempt {attempt+1}/{max_attempts} failed: {e}")
        
        time.sleep(retry_interval)
    
    logger.error(f"{name} failed to become healthy after {max_attempts} attempts")
    return False

def seed_database_if_needed():
    """Check if the database needs seeding and seed it if necessary."""
    try:
        logger.info("Checking if database needs seeding...")
        
        # Run the database seeder in a separate process
        result = subprocess.run(
            [sys.executable, "seed_database.py"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("Database check/seeding completed successfully")
            logger.info(result.stdout.strip())
        else:
            logger.error(f"Database seeding failed with code {result.returncode}")
            logger.error(result.stderr.strip())
    except Exception as e:
        logger.error(f"Error checking/seeding database: {e}")

def main():
    """Main function."""
    logger.info("Starting MCP Assessor Agent API services")
    logger.info(f"Using Flask port: {FLASK_PORT}, FastAPI port: {FASTAPI_PORT}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Check/seed database first
        seed_database_if_needed()
        
        # Start FastAPI service
        logger.info("Starting FastAPI service...")
        fastapi_process = start_fastapi()
        
        # Start Flask service
        logger.info("Starting Flask documentation service...")
        flask_process = start_flask()
        
        # Check service health
        services_healthy = True
        
        if fastapi_process:
            fastapi_healthy = check_service_health(fastapi_process, "FastAPI", FASTAPI_PORT)
            if not fastapi_healthy:
                services_healthy = False
                logger.error("FastAPI service is not responding to health checks")
        else:
            services_healthy = False
            logger.error("FastAPI service failed to start")
        
        if flask_process:
            flask_healthy = check_service_health(flask_process, "Flask", FLASK_PORT)
            if not flask_healthy:
                services_healthy = False
                logger.error("Flask service is not responding to health checks")
        else:
            services_healthy = False
            logger.error("Flask service failed to start")
        
        if services_healthy:
            logger.info("=== All services are running and healthy ===")
            logger.info(f"- Flask documentation: http://localhost:{FLASK_PORT}")
            logger.info(f"- FastAPI service: http://localhost:{FASTAPI_PORT}")
        
        # Monitor and restart services if needed
        while True:
            try:
                # Check FastAPI
                if fastapi_process and fastapi_process.poll() is not None:
                    logger.error(f"FastAPI terminated unexpectedly with code {fastapi_process.returncode}")
                    fastapi_process = start_fastapi()
                
                # Check Flask
                if flask_process and flask_process.poll() is not None:
                    logger.error(f"Flask terminated unexpectedly with code {flask_process.returncode}")
                    flask_process = start_flask()
                
                # Sleep to avoid high CPU usage
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Sleep longer after an error
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        stop_all_processes()
        logger.info("All services have been stopped")

if __name__ == "__main__":
    main()