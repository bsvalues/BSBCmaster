"""
This script is the main entry point for the workflow.
It starts both the FastAPI service and Flask documentation.
"""

import os
import sys
import subprocess
import signal
import time
import threading
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("workflow.log")
    ]
)
logger = logging.getLogger(__name__)

# Global variables to store processes
fastapi_process = None
flask_process = None

# Set FastAPI URL
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")
os.environ["FASTAPI_URL"] = FASTAPI_URL
logger.info(f"FastAPI URL set to: {FASTAPI_URL}")

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
        # Kill any existing processes on port 8000
        try:
            subprocess.run(
                ["fuser", "-k", "8000/tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Killed existing process on port 8000")
        except Exception:
            pass
        
        # Start FastAPI service using our dedicated script
        cmd = ["python", "run_fastapi_service.py"]
        logger.info(f"Starting FastAPI service using dedicated script: {' '.join(cmd)}")
        
        # Set environment variables
        env = os.environ.copy()
        env["FASTAPI_URL"] = "http://localhost:8000"
        
        # Ensure DATABASE_URL is set
        if "DATABASE_URL" in env:
            logger.info("Using existing DATABASE_URL from environment")
        elif all(k in env for k in ["PGHOST", "PGUSER", "PGDATABASE"]):
            pg_user = env.get("PGUSER")
            pg_pass = env.get("PGPASSWORD", "")
            pg_host = env.get("PGHOST")
            pg_port = env.get("PGPORT", "5432")
            pg_db = env.get("PGDATABASE")
            
            db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
            env["DATABASE_URL"] = db_url
            logger.info(f"Constructed DATABASE_URL from PostgreSQL environment variables: {pg_host}:{pg_port}/{pg_db}")
        else:
            logger.warning("Neither DATABASE_URL nor PostgreSQL environment variables found")
        
        fastapi_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False,
            env=env
        )
        
        # Start a thread to monitor and log FastAPI output
        threading.Thread(
            target=log_output,
            args=(fastapi_process, "FastAPI"),
            daemon=True
        ).start()
        
        # Wait for FastAPI to initialize
        logger.info("FastAPI service starting. Waiting for initialization...")
        
        # Wait up to 60 seconds for FastAPI to start up - increased timeout for more reliability
        for attempt in range(60):
            try:
                response = requests.get(f"{FASTAPI_URL}/health", timeout=1)
                if response.status_code == 200:
                    logger.info(f"FastAPI is running and healthy after {attempt+1} attempts: {response.text}")
                    return True
            except requests.exceptions.RequestException:
                if attempt % 10 == 0:  # Log only occasionally to avoid cluttering logs
                    logger.info(f"Waiting for FastAPI (attempt {attempt+1}/60)...")
            time.sleep(1)
            
        # Check if the process is still running
        if fastapi_process and fastapi_process.poll() is None:
            logger.warning("FastAPI process is running but health check failed. Continuing anyway...")
            return True
        else:
            logger.error("FastAPI process has exited unexpectedly")
            return False
    
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {e}")
        return False

def start_flask():
    """Start the Flask documentation application."""
    global flask_process
    
    try:
        # Kill any existing processes on port 5000
        try:
            subprocess.run(
                ["fuser", "-k", "5000/tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("Killed existing process on port 5000")
        except Exception:
            pass
        
        # Start Flask service using gunicorn
        cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]
        logger.info(f"Starting Flask service: {' '.join(cmd)}")
        
        # Set environment variables
        env = os.environ.copy()
        env["FASTAPI_URL"] = "http://localhost:8000"
        
        flask_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False,
            env=env
        )
        
        # Start a thread to monitor and log Flask output
        threading.Thread(
            target=log_output,
            args=(flask_process, "Flask"),
            daemon=True
        ).start()
        
        logger.info("Flask service starting. Waiting for initialization...")
        
        # Wait up to 30 seconds for Flask to start up
        for _ in range(30):
            try:
                response = requests.get("http://localhost:5000/", timeout=1)
                if response.status_code == 200:
                    logger.info("Flask is running and healthy")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
            
        # Check if the process is still running
        if flask_process and flask_process.poll() is None:
            logger.warning("Flask process is running but health check failed. Continuing anyway...")
            return True
        else:
            logger.error("Flask process has exited unexpectedly")
            return False
    
    except Exception as e:
        logger.error(f"Error starting Flask service: {e}")
        return False

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    logger.info("Cleaning up processes...")
    
    if fastapi_process and fastapi_process.poll() is None:
        logger.info("Terminating FastAPI process")
        fastapi_process.terminate()
        try:
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("FastAPI process did not terminate, killing it")
            fastapi_process.kill()
    
    if flask_process and flask_process.poll() is None:
        logger.info("Terminating Flask process")
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Flask process did not terminate, killing it")
            flask_process.kill()
    
    # Exit gracefully if called as a signal handler
    if signum is not None:
        sys.exit(0)

def main():
    """Main function to start both services for the workflow."""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("=" * 80)
    logger.info("Starting MCP Assessor Agent API services")
    logger.info("=" * 80)
    
    # Start FastAPI service first
    logger.info("Starting services separately")
    
    # Start FastAPI service
    if not start_fastapi():
        logger.error("Failed to start FastAPI service")
        return 1
    
    # Start Flask service
    if not start_flask():
        logger.error("Failed to start Flask service")
        cleanup()
        return 1
    
    logger.info("Both services started successfully")
    
    # Monitor the processes
    try:
        while True:
            # Check if either process has exited
            fastapi_running = fastapi_process and fastapi_process.poll() is None
            flask_running = flask_process and flask_process.poll() is None
            
            if not fastapi_running:
                logger.error("FastAPI process has unexpectedly exited")
                cleanup()
                return 1
            
            if not flask_running:
                logger.error("Flask process has unexpectedly exited")
                cleanup()
                return 1
            
            # Sleep briefly before checking again
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())