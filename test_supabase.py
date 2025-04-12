"""
Test script for Supabase integration.

This script tests the Supabase client connection and basic operations.
"""

import os
import logging
from app.db.supabase_client import (
    test_connection, 
    is_connected, 
    fetch_properties,
    get_property_by_id,
    fetch_accounts
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to test Supabase integration."""
    # Check if Supabase URL and key are set
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.warning("Supabase credentials not set. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        logger.info("To set these environment variables in Replit:")
        logger.info("1. Go to the 'Secrets' tab in the 'Tools' panel")
        logger.info("2. Add 'SUPABASE_URL' and 'SUPABASE_ANON_KEY' with your Supabase project URL and anon key")
        return
    
    # Test connection
    logger.info("Testing Supabase connection...")
    if is_connected():
        logger.info("✅ Supabase client initialized successfully")
    else:
        logger.error("❌ Supabase client not initialized")
        return
    
    if test_connection():
        logger.info("✅ Supabase connection test passed")
    else:
        logger.error("❌ Supabase connection test failed")
        return
    
    # Try to fetch properties
    logger.info("Fetching properties...")
    properties = fetch_properties(limit=5)
    if properties:
        logger.info(f"✅ Successfully fetched {len(properties)} properties")
        logger.info(f"First property: {properties[0]}")
    else:
        logger.warning("No properties found. This might be normal if the table is empty.")
    
    # Try to fetch accounts
    logger.info("Fetching accounts...")
    accounts = fetch_accounts(limit=5)
    if accounts:
        logger.info(f"✅ Successfully fetched {len(accounts)} accounts")
        logger.info(f"First account: {accounts[0]}")
    else:
        logger.warning("No accounts found. This might be normal if the table is empty.")

if __name__ == "__main__":
    main()