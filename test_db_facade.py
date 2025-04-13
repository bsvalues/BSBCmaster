"""
Test Database Facade

This script tests the database facade module to ensure it correctly
accesses the database via either Supabase REST API or direct SQL.
"""

import os
import logging
import json
import sys
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the database facade
from app.db.db_facade import (
    test_connection,
    fetch_accounts,
    get_account_by_id,
    get_accounts_by_city,
    get_property_types,
    get_city_statistics,
    get_value_distribution
)

def test_all():
    """Run all tests."""
    logger.info("Testing database facade")
    
    # Test connection
    logger.info("Testing database connection")
    if not test_connection():
        logger.error("Database connection failed")
        return False
    logger.info("Database connection test passed")
    
    # Test fetch accounts
    logger.info("Testing fetch_accounts (limit=3)")
    accounts = fetch_accounts(limit=3)
    if not accounts:
        logger.error("Failed to fetch accounts")
        return False
    logger.info(f"Fetched {len(accounts)} accounts")
    logger.info(f"First account: {json.dumps(accounts[0], indent=2)}")
    
    # Test get account by ID
    if accounts:
        account_id = accounts[0].get('account_id')
        logger.info(f"Testing get_account_by_id with ID: {account_id}")
        account = get_account_by_id(account_id)
        if not account:
            logger.error(f"Failed to get account by ID: {account_id}")
        else:
            logger.info(f"Successfully retrieved account by ID: {account_id}")
    
    # Test get accounts by city
    # First find a city that exists in the data
    cities = set()
    for account in accounts:
        if account.get('property_city'):
            cities.add(account.get('property_city'))
    
    if cities:
        test_city = list(cities)[0]
        logger.info(f"Testing get_accounts_by_city with city: {test_city}")
        city_accounts = get_accounts_by_city(test_city, limit=2)
        if not city_accounts:
            logger.error(f"Failed to get accounts for city: {test_city}")
        else:
            logger.info(f"Successfully retrieved {len(city_accounts)} accounts for city: {test_city}")
    
    # Test get property types
    logger.info("Testing get_property_types")
    property_types = get_property_types()
    if not property_types:
        logger.error("Failed to get property types")
    else:
        logger.info(f"Successfully retrieved {len(property_types)} property types")
        logger.info(f"Property types: {json.dumps(property_types, indent=2)}")
    
    # Test get city statistics
    logger.info("Testing get_city_statistics")
    city_stats = get_city_statistics()
    if not city_stats:
        logger.error("Failed to get city statistics")
    else:
        logger.info(f"Successfully retrieved statistics for {len(city_stats)} cities")
        logger.info(f"City statistics: {json.dumps(city_stats, indent=2)}")
    
    # Test get value distribution
    logger.info("Testing get_value_distribution")
    value_dist = get_value_distribution()
    if not value_dist:
        logger.error("Failed to get value distribution")
    else:
        logger.info(f"Successfully retrieved value distribution")
        logger.info(f"Value distribution: {json.dumps(value_dist, indent=2)}")
    
    logger.info("All tests completed")
    return True

if __name__ == "__main__":
    test_all()