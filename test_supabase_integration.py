"""
Test Supabase Integration

This script tests the integration between our application and the Supabase database.
It performs read operations on existing tables to verify connectivity and data access.
"""

import os
import logging
import sys
import json
import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from app.db.supabase_client import get_supabase_client, is_connected

def test_read_accounts(limit=5):
    """Test reading from the accounts table."""
    logger.info(f"Testing read from accounts table (limit={limit})")
    
    supabase = get_supabase_client()
    
    try:
        # Query accounts table
        response = supabase.table("accounts").select("*").limit(limit).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error reading accounts: {response.error}")
            return False
        
        # Get the data
        accounts = response.data
        
        if not accounts or len(accounts) == 0:
            logger.warning("No accounts found in the database")
            return True
        
        logger.info(f"Successfully read {len(accounts)} accounts from the database")
        logger.info(f"First account: {json.dumps(accounts[0], indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception reading accounts: {str(e)}")
        return False

def test_read_properties(limit=5):
    """Test reading from the properties table."""
    logger.info(f"Testing read from properties table (limit={limit})")
    
    supabase = get_supabase_client()
    
    try:
        # Query properties table
        response = supabase.table("properties").select("*").limit(limit).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error reading properties: {response.error}")
            return False
        
        # Get the data
        properties = response.data
        
        if not properties or len(properties) == 0:
            logger.warning("No properties found in the database")
            return True
        
        logger.info(f"Successfully read {len(properties)} properties from the database")
        logger.info(f"First property: {json.dumps(properties[0], indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception reading properties: {str(e)}")
        return False

def test_read_improvements(limit=5):
    """Test reading from the improvements table."""
    logger.info(f"Testing read from improvements table (limit={limit})")
    
    supabase = get_supabase_client()
    
    try:
        # Query improvements table
        response = supabase.table("improvements").select("*").limit(limit).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error reading improvements: {response.error}")
            return False
        
        # Get the data
        improvements = response.data
        
        if not improvements or len(improvements) == 0:
            logger.warning("No improvements found in the database")
            return True
        
        logger.info(f"Successfully read {len(improvements)} improvements from the database")
        logger.info(f"First improvement: {json.dumps(improvements[0], indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception reading improvements: {str(e)}")
        return False

def test_read_property_images(limit=5):
    """Test reading from the property_images table."""
    logger.info(f"Testing read from property_images table (limit={limit})")
    
    supabase = get_supabase_client()
    
    try:
        # Query property_images table
        response = supabase.table("property_images").select("*").limit(limit).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error reading property_images: {response.error}")
            return False
        
        # Get the data
        property_images = response.data
        
        if not property_images or len(property_images) == 0:
            logger.warning("No property images found in the database")
            return True
        
        logger.info(f"Successfully read {len(property_images)} property images from the database")
        logger.info(f"First property image: {json.dumps(property_images[0], indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception reading property_images: {str(e)}")
        return False

def test_filtered_query():
    """Test a more complex filtered query."""
    logger.info("Testing filtered query on accounts table")
    
    supabase = get_supabase_client()
    
    try:
        # Query accounts with filters
        response = supabase.table("accounts").select("*").filter("property_city", "eq", "Richland").limit(3).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error executing filtered query: {response.error}")
            return False
        
        # Get the data
        filtered_accounts = response.data
        
        if not filtered_accounts or len(filtered_accounts) == 0:
            logger.warning("No accounts found matching the filter")
            return True
        
        logger.info(f"Successfully found {len(filtered_accounts)} accounts matching the filter")
        logger.info(f"First matching account: {json.dumps(filtered_accounts[0], indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception executing filtered query: {str(e)}")
        return False

def test_count_query():
    """Test a count query."""
    logger.info("Testing count query on accounts table")
    
    supabase = get_supabase_client()
    
    try:
        # Execute a count query
        response = supabase.table("accounts").select("count", count="exact").execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error executing count query: {response.error}")
            return False
        
        # Get the count
        count = response.count if hasattr(response, 'count') else None
        
        if count is None:
            logger.warning("Count query did not return a count")
            return False
        
        logger.info(f"Total accounts in the database: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Exception executing count query: {str(e)}")
        return False

def main():
    """Main function to run all tests."""
    logger.info("Starting Supabase integration tests")
    
    # Check Supabase connection
    if not is_connected():
        logger.error("Supabase client not initialized")
        return False
    
    logger.info("Supabase client initialized successfully")
    
    # Run all tests
    tests = [
        test_read_accounts,
        test_read_properties,
        test_read_improvements,
        test_read_property_images,
        test_filtered_query,
        test_count_query
    ]
    
    success_count = 0
    for test_func in tests:
        if test_func():
            success_count += 1
    
    logger.info(f"Tests completed: {success_count}/{len(tests)} successful")
    
    return success_count == len(tests)

if __name__ == "__main__":
    main()