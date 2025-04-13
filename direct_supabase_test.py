"""
Direct Supabase Test

This script creates a direct connection to Supabase using the official Python client
and attempts to query tables using a different approach.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import supabase SDK
try:
    from supabase import create_client, Client
except ImportError:
    logger.error("Supabase SDK not found, attempting to install")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
    from supabase import create_client, Client
    logger.info("Supabase SDK installed successfully")

# Get credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")

logger.info(f"Using Supabase URL: {supabase_url and supabase_url[:25]}...")
logger.info(f"Using Supabase Key: {supabase_key and supabase_key[:10]}...")

if not supabase_url or not supabase_key:
    logger.error("Supabase credentials not found in environment variables")
    exit(1)

try:
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    logger.info("Supabase client created successfully")
    
    # Test auth status
    try:
        auth_response = supabase.auth.get_user()
        logger.info(f"Auth status: {'Authenticated' if auth_response.user else 'Not authenticated'}")
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
    
    # Try to directly query the schema and table metadata
    logger.info("Attempting to query account table with basic select")
    try:
        # Simplest query possible
        response = supabase.from_("accounts").select("*").limit(1).execute()
        
        # Check for data
        if response.data:
            logger.info(f"Success! Found {len(response.data)} records")
            logger.info(f"Sample data: {json.dumps(response.data[0], indent=2)}")
        else:
            logger.warning("Query returned no data")
            
    except Exception as e:
        logger.error(f"Error querying accounts table: {str(e)}")
        
        # Try alternate syntax
        logger.info("Trying alternate query syntax")
        try:
            result = supabase.table("accounts").select("*").limit(1).execute()
            if hasattr(result, 'data') and result.data:
                logger.info(f"Alternate syntax success! Found {len(result.data)} records")
            else:
                logger.warning("Alternate query returned no data")
        except Exception as alt_e:
            logger.error(f"Error with alternate syntax: {str(alt_e)}")
    
    # Try SQL query via RPC
    logger.info("Attempting to use SQL via RPC")
    try:
        # Use RPC function to execute SQL
        result = supabase.rpc("run_sql", {"query": "SELECT * FROM accounts LIMIT 1"}).execute()
        if hasattr(result, 'data') and result.data:
            logger.info(f"SQL via RPC success! Found {len(result.data)} records")
            logger.info(f"Sample data: {json.dumps(result.data[0], indent=2)}")
        else:
            logger.warning("SQL via RPC returned no data")
    except Exception as sql_e:
        logger.error(f"Error with SQL via RPC: {str(sql_e)}")
        
    # List tables in public schema
    logger.info("Listing tables in public schema via SQL")
    try:
        result = supabase.rpc("run_sql", {"query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"}).execute()
        if hasattr(result, 'data') and result.data:
            logger.info(f"Table list: {[table['table_name'] for table in result.data]}")
        else:
            logger.warning("No tables found")
    except Exception as list_e:
        logger.error(f"Error listing tables: {str(list_e)}")
        
except Exception as main_e:
    logger.error(f"Main exception: {str(main_e)}")