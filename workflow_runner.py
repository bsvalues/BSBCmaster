"""
MCP Assessor Agent API - Workflow Runner

This script is specifically designed for the Replit workflow.
It starts the server.py script which runs both the Flask documentation
and FastAPI service in a single process.
"""

import subprocess
import sys
import signal
import logging

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

# Global variable for server process
server_process = None

def signal_handler(signum, frame):
    """Handle signals and clean up."""
    logger.info(f"Received signal {signum}, shutting down...")
    if server_process:
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
        except:
            server_process.kill()
    sys.exit(0)

def main():
    """Main function to run the server."""
    global server_process
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting MCP Assessor Agent API server via workflow runner...")
    
    try:
        # Start the server.py script which handles both services
        cmd = ["python", "server.py"]
        server_process = subprocess.Popen(cmd)
        
        # Wait for the process to complete
        return_code = server_process.wait()
        logger.info(f"Server process exited with code {return_code}")
        return return_code
    
    except Exception as e:
        logger.error(f"Error running server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())