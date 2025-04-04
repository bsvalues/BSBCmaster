#!/usr/bin/env python3
"""
Test script for the enhanced SQL parameterization and execution functions.
This script tests the functionality of the parse_for_parameters and execute_parameterized_query functions.
"""

import requests
import json
import logging
from typing import Dict, Any, List, Tuple
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_parameterized_queries")

# Test API endpoint
API_URL = "http://localhost:5000/api/run-query"

def test_string_parameters() -> None:
    """Test SQL parameter extraction and execution with string values."""
    logger.info("Testing string parameter extraction...")
    
    # Test standard string parameter
    query = """SELECT * FROM parcels WHERE owner_name = 'Jane Smith' LIMIT 5"""
    response = execute_query("postgres", query)
    
    if not response.get("data"):
        logger.error("Failed to execute string parameter query")
        return
    
    logger.info(f"Found {len(response.get('data', []))} results for string parameter query")
    
    # Test multiple string parameters
    query = """SELECT * FROM parcels WHERE owner_name = 'Jane Smith' AND address LIKE '%Main%'"""
    response = execute_query("postgres", query)
    
    logger.info(f"Found {len(response.get('data', []))} results for multiple string parameters query")
    
def test_numeric_parameters() -> None:
    """Test SQL parameter extraction and execution with numeric values."""
    logger.info("Testing numeric parameter extraction...")
    
    # Test numeric parameter
    query = """SELECT * FROM parcels WHERE total_value > 500000 LIMIT 5"""
    response = execute_query("postgres", query)
    
    if not response.get("data"):
        logger.error("Failed to execute numeric parameter query")
        return
    
    logger.info(f"Found {len(response.get('data', []))} results for numeric parameter query")
    
    # Test float parameter
    query = """SELECT * FROM parcels WHERE land_value > 200000.00 LIMIT 5"""
    response = execute_query("postgres", query)
    
    logger.info(f"Found {len(response.get('data', []))} results for float parameter query")
    
def test_mixed_parameters() -> None:
    """Test SQL parameter extraction and execution with mixed parameter types."""
    logger.info("Testing mixed parameter extraction...")
    
    # Test mixed parameters
    query = """
    SELECT * FROM parcels 
    WHERE owner_name = 'John Doe' 
      AND total_value > 500000 
      AND address LIKE '%Oak%'
    LIMIT 5
    """
    response = execute_query("postgres", query)
    
    logger.info(f"Found {len(response.get('data', []))} results for mixed parameters query")
    
    # Test parameters in complex query
    query = """
    SELECT p.* 
    FROM parcels p
    JOIN properties pr ON p.parcel_id = pr.parcel_id  
    WHERE p.total_value BETWEEN 400000 AND 800000
      AND p.zone_code = 'R2'
      AND pr.bedrooms >= 3
    LIMIT 5
    """
    response = execute_query("postgres", query)
    
    logger.info(f"Found {len(response.get('data', []))} results for complex query with parameters")

def execute_query(db_type: str, query: str) -> Dict[str, Any]:
    """
    Execute a query through the API and return the response.
    
    Args:
        db_type: Database type (postgres or mssql)
        query: SQL query to execute
        
    Returns:
        Dict containing the API response
    """
    try:
        # Build the request payload
        payload = {
            "db": db_type,
            "query": query
        }
        
        # Make the API request
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return {"status": "error", "data": [], "count": 0, "truncated": False}
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return {"status": "error", "data": [], "count": 0, "truncated": False}

def run_all_tests() -> None:
    """Run all parameterized query tests."""
    logger.info("Starting parameterized query tests...")
    
    test_string_parameters()
    test_numeric_parameters()
    test_mixed_parameters()
    
    logger.info("All parameterized query tests completed")

if __name__ == "__main__":
    run_all_tests()