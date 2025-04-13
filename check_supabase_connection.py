"""
Check Supabase Connection

This script verifies the Supabase connection and checks if the URL and key are valid.
"""

import os
import logging
import sys
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Check Supabase connection and credentials."""
    logger.info("Checking Supabase connection")
    
    # Check if SUPABASE_URL and SUPABASE_ANON_KEY are set
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not supabase_url:
        logger.error("SUPABASE_URL environment variable is not set")
        return
    
    if not supabase_key:
        logger.error("SUPABASE_ANON_KEY environment variable is not set")
        return
    
    # Print the first few characters of the URL and key for verification
    logger.info(f"SUPABASE_URL starts with: {supabase_url[:25]}...")
    logger.info(f"SUPABASE_ANON_KEY starts with: {supabase_key[:10]}...")
    
    # Try importing the supabase-py package
    try:
        logger.info("Importing supabase package")
        from supabase import create_client, Client
        logger.info("Supabase package imported successfully")
    except ImportError:
        logger.error("Failed to import supabase package")
        logger.info("Trying to install supabase package")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
            logger.info("Supabase package installed successfully")
            from supabase import create_client, Client
        except Exception as e:
            logger.error(f"Failed to install supabase package: {str(e)}")
            return
    
    # Try connecting to Supabase
    try:
        logger.info("Connecting to Supabase")
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client created successfully")
        
        # Try a simple query to check connection
        logger.info("Testing Supabase connection with a simple query")
        # Try to get the current user
        auth_response = supabase.auth.get_user()
        logger.info(f"Auth response status: {getattr(auth_response, 'status_code', 'N/A')}")
        
        logger.info("Supabase connection verified successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        return

if __name__ == "__main__":
    main()