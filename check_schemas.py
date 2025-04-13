"""
Check Schemas in Supabase

This script tries to list all schemas and tables available in the Supabase database
to help us understand what's already set up.
"""

import os
import logging
import sys
import json
import time
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from app.db.supabase_client import get_supabase_client, is_connected

def check_tables_in_schema(schema_name):
    """Check for tables in a specific schema."""
    logger.info(f"Checking for tables in schema '{schema_name}'")
    
    supabase = get_supabase_client()
    
    # Try a few common tables
    for table_name in [
        "accounts", "parcels", "properties", "sales", 
        "assessments", "property_images", "users", "properties"
    ]:
        try:
            full_table_name = f"{schema_name}.{table_name}"
            logger.info(f"Checking table: {full_table_name}")
            
            # Attempt to select from the table
            table_response = supabase.from_(full_table_name).select("*").limit(1).execute()
            
            if hasattr(table_response, 'error') and table_response.error:
                logger.error(f"Table {full_table_name} error: {table_response.error}")
            else:
                logger.info(f"Table {full_table_name} exists and has {len(table_response.data or [])} records")
                # Print the first record's keys to understand the schema
                if table_response.data and len(table_response.data) > 0:
                    logger.info(f"Table {full_table_name} schema: {list(table_response.data[0].keys())}")
        except Exception as e:
            logger.error(f"Exception checking table {full_table_name}: {str(e)}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)

def main():
    """Main function to check schemas in Supabase."""
    logger.info("Checking schemas in Supabase")
    
    # Check Supabase connection
    if not is_connected():
        logger.error("Supabase client not initialized")
        return
    
    # Check common schemas
    for schema in ["public", "auth", "storage", "graphql_public", "realtime", "extensions"]:
        check_tables_in_schema(schema)

if __name__ == "__main__":
    main()