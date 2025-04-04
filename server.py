"""
MCP Assessor Agent API - Workflow-Compatible Server

This script starts both the Flask documentation interface and FastAPI service
using a single-process approach for the Replit workflow environment.
"""

import os
import sys
import logging
import threading
import time
import signal
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('workflow.log')
    ]
)
logger = logging.getLogger(__name__)

# Create Flask application
from flask import Flask, render_template, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24))

# Initialize the app with the extension
db.init_app(app)

# Import models to register them with SQLAlchemy
try:
    from models import Parcel, Property, Sale
except ImportError:
    logger.warning("Could not import models - they may need to be created")

# Create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created or verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Import database routes
try:
    import database
    logger.info("Database routes imported successfully")
except ImportError:
    logger.error("Could not import database routes")
    
    # Provide a simple route if database routes can't be imported
    @app.route('/')
    def index():
        """Simple index route for Flask."""
        return render_template('index.html', title="MCP Assessor Agent API")

@app.route('/api/health')
def health():
    """Health check endpoint for Flask."""
    return jsonify({
        "status": "success",
        "message": "Flask documentation service is operational",
        "timestamp": datetime.utcnow().isoformat()
    })

def seed_database_if_needed():
    """Seed the database if no data exists."""
    try:
        logger.info("Checking if database needs seeding...")
        
        # Run the seeder script
        result = subprocess.run(
            [sys.executable, "seed_database.py"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("Database seeding or verification successful")
            logger.info(result.stdout.strip())
        else:
            logger.error(f"Error seeding database (code {result.returncode})")
            logger.error(result.stderr.strip())
    except Exception as e:
        logger.error(f"Exception during database seeding: {e}")

def start_fastapi():
    """Start the FastAPI service in a background thread."""
    logger.info("Starting FastAPI service in background thread...")
    
    def run_server():
        try:
            import uvicorn
            from app import app as fastapi_app
            
            # Configure uvicorn server
            config = uvicorn.Config(
                app=fastapi_app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                log_config={
                    "version": 1,
                    "formatters": {
                        "default": {
                            "fmt": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                            "datefmt": "%Y-%m-%d %H:%M:%S",
                        }
                    },
                    "handlers": {
                        "default": {
                            "formatter": "default",
                            "class": "logging.StreamHandler",
                            "stream": "ext://sys.stderr",
                        },
                        "file": {
                            "formatter": "default",
                            "class": "logging.FileHandler",
                            "filename": "fastapi.log",
                        }
                    },
                    "loggers": {
                        "uvicorn": {"handlers": ["default", "file"], "level": "INFO"},
                        "uvicorn.error": {"level": "INFO"},
                        "uvicorn.access": {"level": "INFO"},
                    }
                }
            )
            
            # Create server instance
            server = uvicorn.Server(config)
            
            # Write PID to file for possible management
            with open("fastapi.pid", "w") as f:
                f.write(str(os.getpid()))
            
            logger.info("FastAPI service starting on port 8000")
            server.run()
        except Exception as e:
            logger.error(f"Error in FastAPI thread: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Start in daemon thread
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info("FastAPI background thread started")
    return thread

def cleanup_on_exit(signum=None, frame=None):
    """Cleanup resources on exit."""
    logger.info("Shutdown signal received, cleaning up...")
    try:
        # Try to remove PID file if it exists
        if os.path.exists("fastapi.pid"):
            os.unlink("fastapi.pid")
    except Exception as e:
        logger.error(f"Error cleaning up: {e}")
    
    # Exit process
    sys.exit(0)

# Set up signal handlers
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# Set up a route to test FastAPI connection
@app.route('/api/fastapi-test')
def fastapi_test():
    """Test connectivity to the FastAPI service."""
    import requests
    try:
        response = requests.get('http://localhost:8000/health')
        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "FastAPI service is operational",
                "fastapi_response": response.json(),
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"FastAPI responded with status {response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to FastAPI: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# This is the application object that Gunicorn will use
application = app

# When executed directly, start the FastAPI service and then run Flask
if __name__ == "__main__":
    # Seed database first
    seed_database_if_needed()
    
    # Start FastAPI in background thread
    fastapi_thread = start_fastapi()
    
    # Wait a moment for FastAPI to initialize
    time.sleep(3)
    
    # Start Flask (this will block until the program exits)
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting Flask application on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)