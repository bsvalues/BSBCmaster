"""
Supabase Client Integration Module

This module provides a client interface to interact with Supabase
for the MCP Assessor Agent API.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve the Supabase URL and anon key from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Flag to indicate if Supabase is properly configured
is_supabase_configured = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

# Create the Supabase client instance if credentials are available
supabase: Optional[Client] = None
if is_supabase_configured:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        is_supabase_configured = False
else:
    logger.warning("Supabase credentials not found in environment variables")

def get_supabase_client() -> Optional[Client]:
    """
    Get the Supabase client instance.
    
    Returns:
        Optional[Client]: The Supabase client if properly configured, None otherwise
    """
    return supabase

def is_connected() -> bool:
    """
    Check if Supabase is properly configured and connected.
    
    Returns:
        bool: True if Supabase is configured and client is initialized, False otherwise
    """
    return is_supabase_configured and supabase is not None

# Property-related functions
def fetch_properties(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch properties from the 'properties' table.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List[Dict[str, Any]]: List of property records
    """
    if not is_connected():
        logger.error("Cannot fetch properties: Supabase client not initialized")
        return []
    
    try:
        response = supabase.table("properties").select("*").limit(limit).offset(offset).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error fetching properties: {response.error}")
            return []
        return response.data
    except Exception as e:
        logger.error(f"Exception fetching properties: {str(e)}")
        return []

def get_property_by_id(property_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific property by ID.
    
    Args:
        property_id: Unique identifier for the property
        
    Returns:
        Optional[Dict[str, Any]]: Property record if found, None otherwise
    """
    if not is_connected():
        logger.error("Cannot get property: Supabase client not initialized")
        return None
    
    try:
        response = supabase.table("properties").select("*").eq("id", property_id).limit(1).single().execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting property {property_id}: {response.error}")
            return None
        return response.data
    except Exception as e:
        logger.error(f"Exception getting property {property_id}: {str(e)}")
        return None

def create_property(property_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new property record.
    
    Args:
        property_data: Property data to insert
        
    Returns:
        Optional[Dict[str, Any]]: Created property record if successful, None otherwise
    """
    if not is_connected():
        logger.error("Cannot create property: Supabase client not initialized")
        return None
    
    try:
        response = supabase.table("properties").insert(property_data).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error creating property: {response.error}")
            return None
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Exception creating property: {str(e)}")
        return None

def update_property(property_id: str, property_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing property record.
    
    Args:
        property_id: Unique identifier for the property
        property_data: Updated property data
        
    Returns:
        Optional[Dict[str, Any]]: Updated property record if successful, None otherwise
    """
    if not is_connected():
        logger.error("Cannot update property: Supabase client not initialized")
        return None
    
    try:
        response = supabase.table("properties").update(property_data).eq("id", property_id).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error updating property {property_id}: {response.error}")
            return None
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Exception updating property {property_id}: {str(e)}")
        return None

def delete_property(property_id: str) -> bool:
    """
    Delete a property record.
    
    Args:
        property_id: Unique identifier for the property
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    if not is_connected():
        logger.error("Cannot delete property: Supabase client not initialized")
        return False
    
    try:
        response = supabase.table("properties").delete().eq("id", property_id).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error deleting property {property_id}: {response.error}")
            return False
        return True
    except Exception as e:
        logger.error(f"Exception deleting property {property_id}: {str(e)}")
        return False

# Account-related functions
def fetch_accounts(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch accounts from the 'accounts' table.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List[Dict[str, Any]]: List of account records
    """
    if not is_connected():
        logger.error("Cannot fetch accounts: Supabase client not initialized")
        return []
    
    try:
        response = supabase.table("accounts").select("*").limit(limit).offset(offset).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error fetching accounts: {response.error}")
            return []
        return response.data
    except Exception as e:
        logger.error(f"Exception fetching accounts: {str(e)}")
        return []

def get_account_by_id(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific account by ID.
    
    Args:
        account_id: Unique identifier for the account
        
    Returns:
        Optional[Dict[str, Any]]: Account record if found, None otherwise
    """
    if not is_connected():
        logger.error("Cannot get account: Supabase client not initialized")
        return None
    
    try:
        response = supabase.table("accounts").select("*").eq("id", account_id).limit(1).single().execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting account {account_id}: {response.error}")
            return None
        return response.data
    except Exception as e:
        logger.error(f"Exception getting account {account_id}: {str(e)}")
        return None

# Assessment-related functions
def fetch_assessments(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch assessments from the 'assessments' table.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List[Dict[str, Any]]: List of assessment records
    """
    if not is_connected():
        logger.error("Cannot fetch assessments: Supabase client not initialized")
        return []
    
    try:
        response = supabase.table("assessments").select("*").limit(limit).offset(offset).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error fetching assessments: {response.error}")
            return []
        return response.data
    except Exception as e:
        logger.error(f"Exception fetching assessments: {str(e)}")
        return []

def get_assessments_by_property(property_id: str) -> List[Dict[str, Any]]:
    """
    Get assessments for a specific property.
    
    Args:
        property_id: Unique identifier for the property
        
    Returns:
        List[Dict[str, Any]]: List of assessment records for the property
    """
    if not is_connected():
        logger.error("Cannot get assessments: Supabase client not initialized")
        return []
    
    try:
        response = supabase.table("assessments").select("*").eq("property_id", property_id).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting assessments for property {property_id}: {response.error}")
            return []
        return response.data
    except Exception as e:
        logger.error(f"Exception getting assessments for property {property_id}: {str(e)}")
        return []

# Query execution
def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a raw SQL query using Supabase's REST API.
    Note: This function should be used carefully and only with sanitized inputs.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query result rows
    """
    if not is_connected():
        logger.error("Cannot execute query: Supabase client not initialized")
        return []
    
    try:
        # Note: This is a simplified example and may need adjustment
        # based on how Supabase's Python client supports raw queries
        response = supabase.rpc('execute_sql', {'query': query, 'params': params or {}}).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error executing query: {response.error}")
            return []
        return response.data
    except Exception as e:
        logger.error(f"Exception executing query: {str(e)}")
        return []

# Test function
def test_connection() -> bool:
    """
    Test the connection to Supabase by fetching a single record.
    
    Returns:
        bool: True if the connection is working, False otherwise
    """
    if not is_connected():
        logger.error("Cannot test connection: Supabase client not initialized")
        return False
    
    try:
        # Try to fetch a single row from properties table
        response = supabase.table("properties").select("id").limit(1).execute()
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error testing connection: {response.error}")
            return False
        logger.info("Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"Exception testing connection: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the Supabase connection
    if test_connection():
        print("Supabase connection is working properly")
    else:
        print("Supabase connection test failed")