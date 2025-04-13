"""
Database Facade Module

This module provides a unified interface for accessing the database,
attempting to use the Supabase REST API first, and falling back to direct SQL
queries if necessary.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Union, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import clients
from app.db.supabase_client import get_supabase_client, is_connected as is_supabase_connected
import app.db.direct_sql_client as sql_client

def with_fallback(supabase_func: Callable, sql_func: Callable, *args, **kwargs):
    """
    Try to execute a function using the Supabase client first, and fall back to SQL if that fails.
    
    Args:
        supabase_func: Function to call with the Supabase client
        sql_func: Function to call with the SQL client as a fallback
        *args, **kwargs: Arguments to pass to both functions
        
    Returns:
        The result of either function
    """
    # Try Supabase first
    if is_supabase_connected():
        try:
            supabase = get_supabase_client()
            result = supabase_func(supabase, *args, **kwargs)
            return result
        except Exception as e:
            logger.warning(f"Supabase REST API call failed: {str(e)}. Falling back to SQL.")
    else:
        logger.warning("Supabase client not connected. Using SQL fallback.")
    
    # Fall back to SQL
    return sql_func(*args, **kwargs)

# Fetch accounts
def _supabase_fetch_accounts(supabase, limit=100, offset=0):
    """Fetch accounts using Supabase."""
    response = supabase.table("accounts").select("*").limit(limit).offset(offset).execute()
    return response.data if hasattr(response, 'data') else []

def fetch_accounts(limit=100, offset=0):
    """
    Fetch accounts from the database.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of account records
    """
    return with_fallback(
        _supabase_fetch_accounts,
        sql_client.fetch_accounts,
        limit=limit,
        offset=offset
    )

# Get account by ID
def _supabase_get_account_by_id(supabase, account_id):
    """Get account by ID using Supabase."""
    response = supabase.table("accounts").select("*").eq("account_id", account_id).limit(1).execute()
    return response.data[0] if hasattr(response, 'data') and response.data else None

def get_account_by_id(account_id):
    """
    Get a specific account by ID.
    
    Args:
        account_id: Unique identifier for the account
        
    Returns:
        Account record if found, None otherwise
    """
    return with_fallback(
        _supabase_get_account_by_id,
        sql_client.get_account_by_id,
        account_id=account_id
    )

# Get accounts by city
def _supabase_get_accounts_by_city(supabase, city, limit=100):
    """Get accounts by city using Supabase."""
    response = supabase.table("accounts").select("*").eq("property_city", city).limit(limit).execute()
    return response.data if hasattr(response, 'data') else []

def get_accounts_by_city(city, limit=100):
    """
    Get accounts by city.
    
    Args:
        city: City name to filter by
        limit: Maximum number of records to return
        
    Returns:
        List of account records in the specified city
    """
    return with_fallback(
        _supabase_get_accounts_by_city,
        sql_client.get_accounts_by_city,
        city=city,
        limit=limit
    )

# Get property types
def _supabase_get_property_types(supabase):
    """Get property types using Supabase (simplified approach)."""
    # This would typically require a more complex query or server-side function
    response = supabase.table("accounts").select("property_type, count").execute()
    if not hasattr(response, 'data') or not response.data:
        return []
    
    # Process the results (simplified)
    property_types = {}
    for account in response.data:
        property_type = account.get('property_type')
        if property_type:
            if property_type not in property_types:
                property_types[property_type] = {'count': 0, 'total_value': 0}
            property_types[property_type]['count'] += 1
            property_types[property_type]['total_value'] += account.get('assessed_value', 0) or 0
    
    # Calculate averages
    result = []
    for property_type, stats in property_types.items():
        avg_value = stats['total_value'] / stats['count'] if stats['count'] > 0 else 0
        result.append({
            'property_type': property_type,
            'count': stats['count'],
            'average_value': avg_value
        })
    
    return result

def get_property_types():
    """
    Get a list of unique property types and their counts.
    
    Returns:
        List of property types and counts
    """
    # Here we'll just use the SQL client directly since the Supabase
    # implementation would be much more complex for grouped queries
    return sql_client.get_property_types()

# Get city statistics
def get_city_statistics():
    """
    Get statistics for each city.
    
    Returns:
        List of city statistics
    """
    # Again, we'll use SQL directly for these aggregation queries
    return sql_client.get_city_statistics()

# Get value distribution
def get_value_distribution():
    """
    Get the distribution of property values.
    
    Returns:
        Dictionary with value ranges and counts
    """
    return sql_client.get_value_distribution()

# Test connection
def test_connection():
    """
    Test the database connection.
    
    Returns:
        True if either connection method is successful
    """
    supabase_connected = is_supabase_connected()
    if supabase_connected:
        logger.info("Supabase REST API connection successful")
    
    sql_connected = sql_client.test_connection()
    if sql_connected:
        logger.info("Direct SQL connection successful")
    
    return supabase_connected or sql_connected

if __name__ == "__main__":
    if test_connection():
        print("Database connection successful")
    else:
        print("Database connection failed")
    
    accounts = fetch_accounts(limit=5)
    print(f"Fetched {len(accounts)} accounts")
    if accounts:
        print(f"First account: {json.dumps(accounts[0], indent=2)}")
    
    property_types = get_property_types()
    print(f"Property types: {json.dumps(property_types, indent=2)}")
    
    city_stats = get_city_statistics()
    print(f"City statistics: {json.dumps(city_stats, indent=2)}")
    
    value_dist = get_value_distribution()
    print(f"Value distribution: {json.dumps(value_dist, indent=2)}")