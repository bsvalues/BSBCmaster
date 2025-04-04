"""
This script starts the FastAPI service directly using uvicorn.
It's designed to be run as a standalone service in the workflow.
"""

import os
import sys
import logging
import time
import signal
import subprocess
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fastapi.log"),
    ]
)
logger = logging.getLogger(__name__)

def run_fastapi():
    """Run the FastAPI application directly using uvicorn."""
    try:
        # Make sure environment variables are set
        if not os.environ.get("API_KEY"):
            api_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
            logger.warning(f"API_KEY not set, using default: {api_key[:8]}...")
            os.environ["API_KEY"] = api_key
            
        # Set DATABASE_URL if not already set (from environment)
        if not os.environ.get("DATABASE_URL"):
            db_url = os.environ.get("PGHOST")
            if db_url:
                logger.info("Creating DATABASE_URL from PostgreSQL environment variables")
                pg_user = os.environ.get("PGUSER", "postgres")
                pg_pass = os.environ.get("PGPASSWORD", "")
                pg_host = os.environ.get("PGHOST", "localhost")
                pg_port = os.environ.get("PGPORT", "5432")
                pg_db = os.environ.get("PGDATABASE", "postgres")
                
                # Construct PostgreSQL URL
                db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
                os.environ["DATABASE_URL"] = db_url
                logger.info(f"Set DATABASE_URL to PostgreSQL connection at {pg_host}:{pg_port}")
            else:
                logger.warning("No PostgreSQL environment variables found, database features may not work")
        
        # Set other required environment variables for FastAPI
        os.environ["FASTAPI_PORT"] = "8000"
        os.environ["FASTAPI_URL"] = "http://localhost:8000"
        
        logger.info("Starting FastAPI with uvicorn")
        
        # Use subprocess to start uvicorn to avoid blocking this script
        cmd = ["python", "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Log the output
        for line in iter(process.stdout.readline, ""):
            logger.info(f"[FastAPI] {line.strip()}")
            
        # Process has ended
        return_code = process.wait()
        logger.info(f"FastAPI process exited with code {return_code}")
        
        return return_code == 0
        
    except Exception as e:
        logger.error(f"Error starting FastAPI service: {str(e)}", exc_info=True)
        return False

def signal_handler(sig, frame):
    """Handle signals like SIGINT (Ctrl+C)."""
    logger.info("Shutting down FastAPI service...")
    sys.exit(0)

def main():
    """Main function."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run FastAPI
    success = run_fastapi()
    if not success:
        logger.error("Failed to start FastAPI service")
        sys.exit(1)

if __name__ == "__main__":
    main()