"""
Combined runner script for both FastAPI and Flask applications.
This script starts both services and manages them using Python's multiprocessing.
"""

import os
import sys
import time
import signal
import logging
import multiprocessing
import uvicorn
from gunicorn.app.base import BaseApplication
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set environment variables for Flask to communicate with FastAPI
os.environ["FASTAPI_URL"] = "http://127.0.0.1:8000"

def run_fastapi():
    """Start the FastAPI application using uvicorn."""
    logger.info("Starting FastAPI service on port 8000...")
    try:
        # Import the app directly instead of using the command line
        from asgi import app
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"FastAPI service error: {e}")
        sys.exit(1)

def run_flask():
    """Start the Flask application using gunicorn."""
    logger.info("Starting Flask documentation on port 5000...")
    try:
        # Custom Gunicorn application class
        class FlaskApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key, value)

            def load(self):
                return self.application

        # Import Flask app
        from main import app
        
        # Configure Gunicorn
        options = {
            'bind': '0.0.0.0:5000',
            'workers': 1,
            'reload': True,
        }
        
        # Run Gunicorn with the Flask app
        FlaskApplication(app, options).run()
    except Exception as e:
        logger.error(f"Flask service error: {e}")
        sys.exit(1)

def main():
    """Main function to run both services."""
    # Set up processes
    fastapi_process = multiprocessing.Process(target=run_fastapi)
    flask_process = multiprocessing.Process(target=run_flask)
    
    # Start FastAPI
    fastapi_process.start()
    logger.info(f"Started FastAPI process (PID: {fastapi_process.pid})")
    
    # Wait for FastAPI to initialize
    time.sleep(5)
    
    # Start Flask
    flask_process.start()
    logger.info(f"Started Flask process (PID: {flask_process.pid})")
    
    # Function to handle signals
    def signal_handler(sig, frame):
        logger.info("Shutting down services...")
        if fastapi_process.is_alive():
            fastapi_process.terminate()
            logger.info(f"Terminated FastAPI process (PID: {fastapi_process.pid})")
        if flask_process.is_alive():
            flask_process.terminate()
            logger.info(f"Terminated Flask process (PID: {flask_process.pid})")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for both processes to complete
    fastapi_process.join()
    flask_process.join()
    
    # If we get here, it means one of the processes exited
    if not fastapi_process.is_alive():
        logger.error("FastAPI process exited unexpectedly")
    if not flask_process.is_alive():
        logger.error("Flask process exited unexpectedly")
    
    # Clean up
    if fastapi_process.is_alive():
        fastapi_process.terminate()
    if flask_process.is_alive():
        flask_process.terminate()
    
    # Exit with error
    sys.exit(1)

if __name__ == "__main__":
    main()