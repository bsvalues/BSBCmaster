"""
Direct SQL Client for Supabase

This module provides a direct PostgreSQL connection to the Supabase database,
allowing us to execute SQL queries directly when the REST API isn't working properly.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Extract connection details from DATABASE_URL environment variable
def get_connection_params():
    """Extract database connection parameters from DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return None
        
    try:
        # Parse connection parameters from the URL
        # Format: postgresql://username:password@hostname:port/database
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        return db_url
    except Exception as e:
        logger.error(f"Error parsing DATABASE_URL: {str(e)}")
        return None

def get_connection():
    """Get a PostgreSQL connection to Supabase."""
    conn_string = get_connection_params()
    if not conn_string:
        return None
        
    try:
        # Connect to the database
        conn = psycopg2.connect(conn_string)
        logger.info("Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None

def execute_query(query: str, params: Optional[Union[Dict[str, Any], List, Tuple]] = None) -> List[Dict[str, Any]]:
    """
    Execute a SQL query and return the results as a list of dictionaries.
    
    Args:
        query: SQL query to execute
        params: Query parameters (dict, list, or tuple)
        
    Returns:
        List of dictionaries with the query results
    """
    conn = get_connection()
    if not conn:
        logger.error("Cannot execute query: Failed to connect to database")
        return []
        
    try:
        # Create a cursor with dictionary-like results
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Execute the query
            if isinstance(params, dict):
                # For named parameters
                cursor.execute(query, params)
            elif params is not None:
                # For positional parameters
                cursor.execute(query, params)
            else:
                # No parameters
                cursor.execute(query)
            
            # Fetch results
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            records = [dict(row) for row in results]
            
            return records
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return []
    finally:
        # Close the connection
        conn.close()

def fetch_accounts(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch accounts from the accounts table.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of account records
    """
    query = """
    SELECT *
    FROM accounts
    ORDER BY id
    LIMIT %s OFFSET %s
    """
    
    return execute_query(query, [limit, offset])

def get_account_by_id(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific account by ID.
    
    Args:
        account_id: Unique identifier for the account
        
    Returns:
        Account record if found, None otherwise
    """
    query = """
    SELECT *
    FROM accounts
    WHERE account_id = %s
    LIMIT 1
    """
    
    results = execute_query(query, [account_id])
    return results[0] if results else None

def get_accounts_by_city(city: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get accounts by city.
    
    Args:
        city: City name to filter by
        limit: Maximum number of records to return
        
    Returns:
        List of account records in the specified city
    """
    query = """
    SELECT *
    FROM accounts
    WHERE property_city = %s
    ORDER BY id
    LIMIT %s
    """
    
    return execute_query(query, [city, limit])

def get_property_types() -> List[Dict[str, Any]]:
    """
    Get a list of unique property types and their counts.
    
    Returns:
        List of property types and counts
    """
    query = """
    SELECT property_type, COUNT(*) as count, AVG(assessed_value) as average_value
    FROM accounts
    WHERE property_type IS NOT NULL
    GROUP BY property_type
    ORDER BY count DESC
    """
    
    return execute_query(query, {})

def get_city_statistics() -> List[Dict[str, Any]]:
    """
    Get statistics for each city.
    
    Returns:
        List of city statistics
    """
    query = """
    SELECT 
        property_city,
        COUNT(*) as count,
        AVG(assessed_value) as average_value,
        MIN(assessed_value) as min_value,
        MAX(assessed_value) as max_value
    FROM accounts
    WHERE property_city IS NOT NULL
    GROUP BY property_city
    ORDER BY count DESC
    """
    
    return execute_query(query, {})

def get_value_distribution() -> Dict[str, int]:
    """
    Get the distribution of property values.
    
    Returns:
        Dictionary with value ranges and counts
    """
    query = """
    SELECT
        CASE
            WHEN assessed_value < 100000 THEN 'Under $100K'
            WHEN assessed_value < 250000 THEN '$100K - $250K'
            WHEN assessed_value < 500000 THEN '$250K - $500K'
            WHEN assessed_value < 1000000 THEN '$500K - $1M'
            ELSE 'Over $1M'
        END as range,
        COUNT(*) as count
    FROM accounts
    WHERE assessed_value IS NOT NULL
    GROUP BY range
    ORDER BY 
        CASE range
            WHEN 'Under $100K' THEN 1
            WHEN '$100K - $250K' THEN 2
            WHEN '$250K - $500K' THEN 3
            WHEN '$500K - $1M' THEN 4
            WHEN 'Over $1M' THEN 5
        END
    """
    
    results = execute_query(query, {})
    
    # Convert to dictionary
    distribution = {
        "Under $100K": 0,
        "$100K - $250K": 0,
        "$250K - $500K": 0,
        "$500K - $1M": 0,
        "Over $1M": 0
    }
    
    for row in results:
        distribution[row["range"]] = row["count"]
    
    return distribution

def test_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    conn = get_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result is None:
                logger.error("No result returned from test query")
                return False
            return result[0] == 1
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # Test the connection
    if test_connection():
        print("Connection test successful")
    else:
        print("Connection test failed")
        
    # Test fetching accounts
    accounts = fetch_accounts(limit=5)
    print(f"Fetched {len(accounts)} accounts")
    if accounts:
        print(f"First account: {json.dumps(accounts[0], indent=2)}")
        
    # Test property types
    property_types = get_property_types()
    print(f"Property types: {json.dumps(property_types, indent=2)}")
    
    # Test city statistics
    city_stats = get_city_statistics()
    print(f"City statistics: {json.dumps(city_stats, indent=2)}")
    
    # Test value distribution
    value_dist = get_value_distribution()
    print(f"Value distribution: {json.dumps(value_dist, indent=2)}")