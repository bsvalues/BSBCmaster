"""
Test Supabase CRUD Operations

This script verifies that the Supabase integration is working correctly
by testing Create, Read, Update, and Delete operations on the accounts table.
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

def test_accounts_operations():
    """Test CRUD operations on the accounts table."""
    logger.info("Testing CRUD operations on accounts table")
    
    # Check Supabase connection
    if not is_connected():
        logger.error("Supabase client not initialized")
        return False
    
    supabase = get_supabase_client()
    
    try:
        # Create a test account
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        test_account_id = f"TEST{timestamp}"
        
        account_data = {
            "account_id": test_account_id,
            "owner_name": "Test Owner",
            "property_address": "123 Test St",
            "property_city": "Test City",
            "property_type": "Residential",
            "latitude": 47.6062,
            "longitude": -122.3321,
            "assessment_year": 2025,
            "assessed_value": 100000,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        logger.info(f"Creating test account with ID: {test_account_id}")
        response = supabase.table("accounts").insert(account_data).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error creating test account: {response.error}")
            return False
        
        logger.info("Test account created successfully")
        
        # Read the test account
        logger.info(f"Reading test account with ID: {test_account_id}")
        read_response = supabase.table("accounts").select("*").eq("account_id", test_account_id).execute()
        
        if hasattr(read_response, 'error') and read_response.error:
            logger.error(f"Error reading test account: {read_response.error}")
            return False
        
        if read_response.data and len(read_response.data) > 0:
            logger.info("Test account read successfully")
            logger.info(f"Account data: {json.dumps(read_response.data[0], indent=2)}")
        else:
            logger.error("Test account not found")
            return False
        
        # Update the test account
        logger.info(f"Updating test account with ID: {test_account_id}")
        update_data = {
            "owner_name": "Updated Owner",
            "assessed_value": 110000
        }
        
        update_response = supabase.table("accounts").update(update_data).eq("account_id", test_account_id).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            logger.error(f"Error updating test account: {update_response.error}")
            return False
        
        logger.info("Test account updated successfully")
        logger.info(f"Updated account data: {json.dumps(update_response.data[0], indent=2)}")
        
        # Delete the test account
        logger.info(f"Deleting test account with ID: {test_account_id}")
        delete_response = supabase.table("accounts").delete().eq("account_id", test_account_id).execute()
        
        if hasattr(delete_response, 'error') and delete_response.error:
            logger.error(f"Error deleting test account: {delete_response.error}")
            return False
        
        logger.info("Test account deleted successfully")
        logger.info("CRUD operations test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Exception testing CRUD operations: {str(e)}")
        return False

if __name__ == "__main__":
    test_accounts_operations()