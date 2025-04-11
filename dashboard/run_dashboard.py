#!/usr/bin/env python3
"""
Run the Benton County Assessor's Office AI Platform Dashboard

This script starts the Streamlit-based system monitoring dashboard.
"""

import os
import sys
import logging
import subprocess
import streamlit.web.bootstrap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dashboard_runner")

def main():
    """Main function to run the dashboard."""
    # Create log directory
    os.makedirs("logs", exist_ok=True)
    
    # Create data directory for Core Hub
    os.makedirs("data/core", exist_ok=True)
    
    logger.info("Starting Benton County Assessor's Office AI Platform Dashboard")
    
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Path to the dashboard script
        dashboard_script = os.path.join(script_dir, "system_monitor.py")
        
        # Check if the dashboard script exists
        if not os.path.exists(dashboard_script):
            logger.error(f"Dashboard script not found: {dashboard_script}")
            sys.exit(1)
        
        logger.info(f"Running dashboard script: {dashboard_script}")
        
        # Run the Streamlit app
        sys.argv = ["streamlit", "run", dashboard_script, "--server.port=8501", "--server.address=0.0.0.0"]
        streamlit.web.bootstrap.run()
        
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()