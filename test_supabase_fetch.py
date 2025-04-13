"""
Test script to verify Supabase fetch operations after client update

This script tests the updated Supabase client to verify that the from_() method works correctly
for fetching data from tables in the public schema.
"""

import logging
from app.db.supabase_client import (
    is_connected, 
    fetch_properties,
    fetch_accounts,
    fetch_assessments
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to test Supabase fetch operations."""
    logger.info("Testing Supabase client with updated from_() method")
    
    if not is_connected():
        logger.error("Supabase client is not connected")
        return
    
    # Test fetch_properties
    logger.info("Fetching properties (limit=5)...")
    properties = fetch_properties(limit=5)
    logger.info(f"Fetched {len(properties)} properties")
    if properties:
        logger.info(f"First property: {properties[0]}")
    
    # Test fetch_accounts
    logger.info("Fetching accounts (limit=5)...")
    accounts = fetch_accounts(limit=5)
    logger.info(f"Fetched {len(accounts)} accounts")
    if accounts:
        logger.info(f"First account: {accounts[0]}")
    
    # Test fetch_assessments
    logger.info("Fetching assessments (limit=5)...")
    assessments = fetch_assessments(limit=5)
    logger.info(f"Fetched {len(assessments)} assessments")
    if assessments:
        logger.info(f"First assessment: {assessments[0]}")

if __name__ == "__main__":
    main()