"""
Import Property Assessment Data from FTP

This script connects to the configured FTP server and imports property assessment data
into the MCP Assessor Agent API database. It reads connection details from environment
variables and handles the import process.
"""

import os
import logging
import sys
from app.ftp_data_importer import import_ftp_data
from flask import Flask
from app_setup import db, app as flask_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_env_var(var_name, default=None):
    """Get environment variable with fallback to default."""
    value = os.environ.get(var_name, default)
    if value is None:
        logger.error(f"Environment variable {var_name} is not set")
        sys.exit(1)
    return value

def main():
    """Main entry point for the script."""
    logger.info("Starting FTP data import process")
    
    # Get FTP connection details from environment variables
    ftp_host = get_env_var('FTP_HOST', 'spatialest.com')
    ftp_user = get_env_var('FTP_USERNAME')
    ftp_password = get_env_var('FTP_PASSWORD')
    ftp_directory = get_env_var('FTP_DIRECTORY', '/')
    
    logger.info(f"Connecting to FTP server: {ftp_host}")
    
    with flask_app.app_context():
        try:
            # Run the import process
            results = import_ftp_data(
                ftp_host=ftp_host,
                ftp_user=ftp_user,
                ftp_password=ftp_password,
                ftp_directory=ftp_directory
            )
            
            # Log results
            for data_type, count in results.items():
                logger.info(f"Imported {count} {data_type} records")
                
            logger.info("FTP data import completed successfully")
            
        except Exception as e:
            logger.error(f"Error during FTP data import: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()