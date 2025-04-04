"""
MCP Assessor Agent API - Standalone Server for Replit

This script runs both the FastAPI and Flask components without relying on
workflow mechanisms. This creates a single-file entry point for deployment.
"""

import os
import logging
import threading
import time
import subprocess
import signal
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log"),
    ]
)
logger = logging.getLogger(__name__)

# Global flag to track if the app should continue running
keep_running = True

# Load environment variables
load_dotenv()

# Set default API key if not present
api_key = os.environ.get("API_KEY")
if not api_key:
    custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
    logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
    os.environ["API_KEY"] = custom_key

def run_flask_server():
    """Run the Flask application using gunicorn."""
    try:
        logger.info("Starting Flask documentation on port 5000...")
        from app_setup import app
        import gunicorn.app.base
        
        # Import routes from database.py
        from database import *  # Import all routes
        
        # Create a custom Gunicorn application
        class FlaskApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key.lower(), value)

            def load(self):
                return self.application
        
        # Run the Flask app with gunicorn
        options = {
            'bind': '0.0.0.0:5000',
            'workers': 1,
            'accesslog': '-',
            'errorlog': '-',
            'reload': True,
            'loglevel': 'info',
        }
        
        FlaskApplication(app, options).run()
        
    except Exception as e:
        logger.error(f"Error running Flask server: {str(e)}")
        # If Flask fails, stop the entire application
        global keep_running
        keep_running = False

def run_fastapi_server():
    """Run the FastAPI application using uvicorn."""
    try:
        logger.info("Starting FastAPI service on port 8000...")
        from app import app
        import uvicorn
        
        # Run the FastAPI app with uvicorn
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"Error running FastAPI server: {str(e)}")
        # If FastAPI fails, allow Flask to continue running

def seed_database_if_needed():
    """Seed the database if needed."""
    try:
        # Import after environment variables are set
        from models import Parcel
        from app_setup import app, db
        
        with app.app_context():
            parcel_count = Parcel.query.count()
            if parcel_count == 0:
                logger.info("No parcels found in database. Running seed script...")
                subprocess.run(["python", "seed_database.py"], check=True)
                logger.info("Database seeded successfully")
            else:
                logger.info(f"Database already has {parcel_count} parcels. No seeding needed.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")

def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info("Received termination signal, shutting down...")
    global keep_running
    keep_running = False
    sys.exit(0)

def main():
    """Main entry point - starts both servers in parallel."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("Starting MCP Assessor Agent API services...")
    logger.info("=" * 60)
    
    # Check database tables and seed if needed
    seed_database_if_needed()
    
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi_server)
    fastapi_thread.daemon = True  # This makes the thread exit when the main program exits
    fastapi_thread.start()
    
    # Allow FastAPI to initialize
    time.sleep(3)
    
    # Start Flask in the main thread
    run_flask_server()
    
    # If we get here, it means the Flask server has stopped
    logger.info("Flask server has stopped. Shutting down...")

if __name__ == "__main__":
    main()