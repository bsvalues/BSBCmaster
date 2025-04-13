"""
Test script to check direct SQL access to database tables

This script tests direct SQL access to verify the tables exist and can be queried.
"""

import logging
import os
from app.db.direct_sql_client import execute_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to test direct SQL access."""
    logger.info("Testing direct SQL access to database tables")
    
    # Test properties table
    logger.info("Querying properties table...")
    properties_query = "SELECT * FROM properties LIMIT 5"
    properties = execute_query(properties_query)
    logger.info(f"Found {len(properties)} properties")
    if properties:
        logger.info(f"First property: {properties[0]}")
    
    # Test accounts table
    logger.info("Querying accounts table...")
    accounts_query = "SELECT * FROM accounts LIMIT 5"
    accounts = execute_query(accounts_query)
    logger.info(f"Found {len(accounts)} accounts")
    if accounts:
        logger.info(f"First account: {accounts[0]}")
    
    # Check table list in database
    logger.info("Querying all tables in the database...")
    tables_query = """
    SELECT schemaname, tablename 
    FROM pg_catalog.pg_tables 
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schemaname, tablename
    """
    tables = execute_query(tables_query)
    logger.info(f"Found {len(tables)} tables")
    for table in tables:
        logger.info(f"Schema: {table['schemaname']}, Table: {table['tablename']}")

if __name__ == "__main__":
    main()