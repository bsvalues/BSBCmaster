"""
Explore Supabase Tables

This script queries the Supabase database to list all available tables
and their structure to help us understand the existing database schema.
"""

import os
import logging
import sys
import json
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from app.db.supabase_client import get_supabase_client, is_connected

def list_tables():
    """List all tables in the Supabase database."""
    logger.info("Listing all tables in Supabase")
    
    # Check Supabase connection
    if not is_connected():
        logger.error("Supabase client not initialized")
        return
    
    supabase = get_supabase_client()
    
    try:
        # Query the information_schema.tables view to get all tables
        response = supabase.rpc(
            'list_tables'
        ).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error listing tables: {response.error}")
            
            # Try an alternative approach
            logger.info("Trying to list known tables directly")
            for table_name in [
                "accounts", "parcels", "properties", "sales", 
                "assessments", "property_images", "users"
            ]:
                try:
                    table_response = supabase.table(table_name).select("*").limit(1).execute()
                    if hasattr(table_response, 'error') and table_response.error:
                        logger.error(f"Table {table_name} error: {table_response.error}")
                    else:
                        logger.info(f"Table {table_name} exists and has {len(table_response.data or [])} records")
                        # Print the first record's keys to understand the schema
                        if table_response.data and len(table_response.data) > 0:
                            logger.info(f"Table {table_name} schema: {list(table_response.data[0].keys())}")
                except Exception as e:
                    logger.error(f"Exception checking table {table_name}: {str(e)}")
            
            return
        
        # Process the result
        tables = response.data
        if tables:
            logger.info(f"Found {len(tables)} tables in Supabase")
            for table in tables:
                logger.info(f"Table: {table}")
        else:
            logger.info("No tables found in Supabase")
        
    except Exception as e:
        logger.error(f"Exception listing tables: {str(e)}")
        
        # Try an alternative approach
        logger.info("Trying to list known tables directly")
        for table_name in [
            "accounts", "parcels", "properties", "sales", 
            "assessments", "property_images", "users"
        ]:
            try:
                table_response = supabase.table(table_name).select("*").limit(1).execute()
                if hasattr(table_response, 'error') and table_response.error:
                    logger.error(f"Table {table_name} error: {table_response.error}")
                else:
                    logger.info(f"Table {table_name} exists and has {len(table_response.data or [])} records")
                    # Print the first record's keys to understand the schema
                    if table_response.data and len(table_response.data) > 0:
                        logger.info(f"Table {table_name} schema: {list(table_response.data[0].keys())}")
            except Exception as e:
                logger.error(f"Exception checking table {table_name}: {str(e)}")

if __name__ == "__main__":
    list_tables()