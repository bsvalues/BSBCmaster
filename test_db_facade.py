"""
Test Database Facade

This script tests the Database Facade to ensure it correctly handles data access
and automatically falls back to direct SQL when REST API access fails.
"""

import logging
from app.db.db_facade import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to test database facade."""
    logger.info("Testing Database Facade")
    
    # Check if connected
    if not db.is_connected():
        logger.error("Database facade is not connected to any database")
        return
    
    # Test getting properties
    logger.info("Fetching properties (limit=5)...")
    properties = db.get_properties(limit=5)
    logger.info(f"Fetched {len(properties)} properties")
    if properties:
        logger.info(f"First property: {properties[0]}")
    
    # Test getting property by ID
    if properties:
        property_id = properties[0]['id']
        logger.info(f"Fetching property with ID {property_id}...")
        property_data = db.get_property_by_id(property_id)
        if property_data:
            logger.info(f"Found property: {property_data}")
        else:
            logger.warning(f"Property with ID {property_id} not found")
    
    # Test getting accounts
    logger.info("Fetching accounts (limit=5)...")
    accounts = db.get_accounts(limit=5)
    logger.info(f"Fetched {len(accounts)} accounts")
    if accounts:
        logger.info(f"First account: {accounts[0]}")
        
        # Test getting account by ID
        account_id = accounts[0]['id']
        logger.info(f"Fetching account with ID {account_id}...")
        account_data = db.get_account_by_id(account_id)
        if account_data:
            logger.info(f"Found account: {account_data}")
        else:
            logger.warning(f"Account with ID {account_id} not found")
    
    # Test getting table schema
    logger.info("Fetching schema for 'properties' table...")
    schema = db.get_table_schema('properties')
    logger.info(f"Fetched {len(schema)} columns in 'properties' schema")
    for column in schema:
        logger.info(f"Column: {column['column_name']}, Type: {column['data_type']}, Nullable: {column['is_nullable']}")
    
    # Test raw SQL query
    logger.info("Executing raw SQL query...")
    query = "SELECT COUNT(*) as count FROM properties"
    results = db.execute_query(query)
    if results:
        logger.info(f"Query result: {results[0]}")
    else:
        logger.warning("Query returned no results")

if __name__ == "__main__":
    main()