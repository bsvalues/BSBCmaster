"""
Database Facade Module

This module provides a unified facade over Supabase client and direct SQL access,
allowing the application to use the most reliable method depending on circumstances.
It automatically falls back to direct SQL connections when REST API fails.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable

from .supabase_client import (
    get_supabase_client,
    is_connected as is_supabase_connected,
    test_connection as test_supabase_connection
)
from .direct_sql_client import (
    execute_query,
    is_connected as is_sql_connected
)
from .json_utils import encode_decimal_datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for table schema information
_schema_cache = {}

class DatabaseFacade:
    """
    Unified database interface that automatically chooses the best access method.
    
    This facade will try Supabase REST API first (faster, more efficient),
    but fall back to direct SQL queries if the REST API access fails (more reliable).
    """
    
    @staticmethod
    def is_connected() -> bool:
        """
        Check if either database connection method is available.
        
        Returns:
            bool: True if at least one connection method is available, False otherwise
        """
        return is_supabase_connected() or is_sql_connected()
    
    @staticmethod
    def get_properties(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get properties from the database using the best available method.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List[Dict[str, Any]]: List of property records
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import fetch_properties
                properties = fetch_properties(limit=limit, offset=offset)
                if properties:
                    logger.info(f"Successfully fetched {len(properties)} properties via Supabase REST API")
                    return properties
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM properties LIMIT %(limit)s OFFSET %(offset)s"
            params = {"limit": limit, "offset": offset}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list):
                logger.info(f"Successfully fetched {len(results)} properties via direct SQL")
                return encode_decimal_datetime(results)
            elif isinstance(results, dict):
                # If we got a single dict, wrap it in a list
                logger.info("Successfully fetched 1 property via direct SQL")
                return encode_decimal_datetime([results])
            else:
                # Empty or unexpected result
                return []
                
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return []
    
    @staticmethod
    def get_property_by_id(property_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get a specific property by ID using the best available method.
        
        Args:
            property_id: Unique identifier for the property
            
        Returns:
            Optional[Dict[str, Any]]: Property record if found, None otherwise
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import get_property_by_id
                property_data = get_property_by_id(str(property_id))
                if property_data:
                    logger.info(f"Successfully fetched property {property_id} via Supabase REST API")
                    return property_data
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM properties WHERE id = %(property_id)s"
            params = {"property_id": property_id}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list) and results:
                logger.info(f"Successfully fetched property {property_id} via direct SQL")
                return encode_decimal_datetime(results[0])
            elif isinstance(results, dict):
                logger.info(f"Successfully fetched property {property_id} via direct SQL")
                return encode_decimal_datetime(results)
            return None
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return None
    
    @staticmethod
    def get_accounts(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get accounts from the database using the best available method.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List[Dict[str, Any]]: List of account records
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import fetch_accounts
                accounts = fetch_accounts(limit=limit, offset=offset)
                if accounts:
                    logger.info(f"Successfully fetched {len(accounts)} accounts via Supabase REST API")
                    return accounts
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM accounts LIMIT %(limit)s OFFSET %(offset)s"
            params = {"limit": limit, "offset": offset}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list):
                logger.info(f"Successfully fetched {len(results)} accounts via direct SQL")
                return encode_decimal_datetime(results)
            elif isinstance(results, dict):
                # If we got a single dict, wrap it in a list
                logger.info("Successfully fetched 1 account via direct SQL")
                return encode_decimal_datetime([results])
            else:
                # Empty or unexpected result
                return []
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return []
    
    @staticmethod
    def get_account_by_id(account_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get a specific account by ID using the best available method.
        
        Args:
            account_id: Unique identifier for the account
            
        Returns:
            Optional[Dict[str, Any]]: Account record if found, None otherwise
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import get_account_by_id
                account_data = get_account_by_id(str(account_id))
                if account_data:
                    logger.info(f"Successfully fetched account {account_id} via Supabase REST API")
                    return account_data
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM accounts WHERE id = %(account_id)s"
            params = {"account_id": account_id}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list) and results:
                logger.info(f"Successfully fetched account {account_id} via direct SQL")
                return encode_decimal_datetime(results[0])
            elif isinstance(results, dict):
                logger.info(f"Successfully fetched account {account_id} via direct SQL")
                return encode_decimal_datetime(results)
            return None
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return None
    
    @staticmethod
    def get_assessments(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get assessments from the database using the best available method.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List[Dict[str, Any]]: List of assessment records
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import fetch_assessments
                assessments = fetch_assessments(limit=limit, offset=offset)
                if assessments:
                    logger.info(f"Successfully fetched {len(assessments)} assessments via Supabase REST API")
                    return assessments
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM assessments LIMIT %(limit)s OFFSET %(offset)s"
            params = {"limit": limit, "offset": offset}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list):
                logger.info(f"Successfully fetched {len(results)} assessments via direct SQL")
                return encode_decimal_datetime(results)
            elif isinstance(results, dict):
                # If we got a single dict, wrap it in a list
                logger.info("Successfully fetched 1 assessment via direct SQL")
                return encode_decimal_datetime([results])
            else:
                # Empty or unexpected result
                return []
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return []
    
    @staticmethod
    def get_assessments_by_property(property_id: Union[str, int]) -> List[Dict[str, Any]]:
        """
        Get assessments for a specific property using the best available method.
        
        Args:
            property_id: Unique identifier for the property
            
        Returns:
            List[Dict[str, Any]]: List of assessment records for the property
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                from .supabase_client import get_assessments_by_property
                assessments = get_assessments_by_property(str(property_id))
                if assessments:
                    logger.info(f"Successfully fetched assessments for property {property_id} via Supabase REST API")
                    return assessments
            except Exception as e:
                logger.warning(f"Supabase REST API fetch failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "SELECT * FROM assessments WHERE property_id = %(property_id)s"
            params = {"property_id": property_id}
            results = execute_query(query, params)
            
            # Handle different result types
            if isinstance(results, list):
                logger.info(f"Successfully fetched {len(results)} assessments for property {property_id} via direct SQL")
                return encode_decimal_datetime(results)
            elif isinstance(results, dict):
                # If we got a single dict, wrap it in a list
                logger.info(f"Successfully fetched 1 assessment for property {property_id} via direct SQL")
                return encode_decimal_datetime([results])
            else:
                # Empty or unexpected result
                return []
        except Exception as e:
            logger.error(f"Direct SQL fetch failed: {str(e)}")
            return []
    
    @staticmethod
    def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query using the best available method.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List[Dict[str, Any]]: Query result rows
        """
        # For raw queries, direct SQL is always more reliable
        try:
            results = execute_query(query, params)
            
            # Handle different result types correctly
            if isinstance(results, list):
                logger.info(f"Successfully executed query via direct SQL with {len(results)} results")
                return encode_decimal_datetime(results)
            elif isinstance(results, dict):
                # If we got a single dict, wrap it in a list
                logger.info("Successfully executed query via direct SQL with 1 result")
                return encode_decimal_datetime([results])
            else:
                # Empty or unexpected result
                logger.info("Successfully executed query via direct SQL with 0 results")
                return []
                
        except Exception as e:
            logger.error(f"Direct SQL query failed: {str(e)}")
            return []
    
    @staticmethod
    def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List[Dict[str, Any]]: List of column definitions for the table
        """
        # Use cache if available
        if table_name in _schema_cache:
            return _schema_cache[table_name]
        
        # Get schema via direct SQL
        try:
            query = """
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM 
                information_schema.columns
            WHERE 
                table_schema = 'public'
                AND table_name = %(table_name)s
            ORDER BY 
                ordinal_position;
            """
            params = {"table_name": table_name}
            results = execute_query(query, params)
            if results:
                logger.info(f"Successfully fetched schema for table {table_name}")
                _schema_cache[table_name] = results
                return results
            else:
                logger.warning(f"No schema found for table {table_name}")
                return []
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            return []
    
    @staticmethod
    def create_record(table_name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new record in the specified table.
        
        Args:
            table_name: Name of the table
            data: Record data to insert
            
        Returns:
            Optional[Dict[str, Any]]: Created record if successful, None otherwise
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                client = get_supabase_client()
                if client:
                    response = client.from_(table_name).insert(data).execute()
                    if hasattr(response, 'data') and response.data:
                        logger.info(f"Successfully created record in {table_name} via Supabase REST API")
                        return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase REST API create failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            # Build INSERT query with proper parameterization
            columns = ', '.join(data.keys())
            placeholders = ', '.join([f"%({k})s" for k in data.keys()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
            results = execute_query(query, data)
            if results and len(results) > 0:
                logger.info(f"Successfully created record in {table_name} via direct SQL")
                # Safely access the first element
                return encode_decimal_datetime(results[0]) if isinstance(results[0], dict) else None
            return None
        except Exception as e:
            logger.error(f"Direct SQL create failed: {str(e)}")
            return None
    
    @staticmethod
    def update_record(table_name: str, record_id: Union[str, int], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing record in the specified table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            data: Updated record data
            
        Returns:
            Optional[Dict[str, Any]]: Updated record if successful, None otherwise
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                client = get_supabase_client()
                if client:
                    response = client.from_(table_name).update(data).eq('id', record_id).execute()
                    if hasattr(response, 'data') and response.data:
                        logger.info(f"Successfully updated record {record_id} in {table_name} via Supabase REST API")
                        return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase REST API update failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            # Build UPDATE query with proper parameterization
            set_clause = ', '.join([f"{k} = %({k})s" for k in data.keys()])
            query = f"UPDATE {table_name} SET {set_clause} WHERE id = %(record_id)s RETURNING *"
            # Add record_id to the parameters
            params = data.copy()
            params['record_id'] = record_id
            results = execute_query(query, params)
            if results and len(results) > 0:
                logger.info(f"Successfully updated record {record_id} in {table_name} via direct SQL")
                # Safely access the first element
                return encode_decimal_datetime(results[0]) if isinstance(results[0], dict) else None
            return None
        except Exception as e:
            logger.error(f"Direct SQL update failed: {str(e)}")
            return None
    
    @staticmethod
    def delete_record(table_name: str, record_id: Union[str, int]) -> bool:
        """
        Delete a record from the specified table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        # First try Supabase REST API (if it's working)
        if is_supabase_connected() and test_supabase_connection():
            try:
                client = get_supabase_client()
                if client:
                    response = client.from_(table_name).delete().eq('id', record_id).execute()
                    if hasattr(response, 'data'):
                        logger.info(f"Successfully deleted record {record_id} from {table_name} via Supabase REST API")
                        return True
            except Exception as e:
                logger.warning(f"Supabase REST API delete failed: {str(e)}, falling back to direct SQL")
        
        # Fall back to direct SQL query
        try:
            query = "DELETE FROM %(table)s WHERE id = %(record_id)s RETURNING id"
            params = {'record_id': record_id, 'table': table_name}
            results = execute_query(query, params)
            if results and len(results) > 0:
                logger.info(f"Successfully deleted record {record_id} from {table_name} via direct SQL")
                return True
            return False
        except Exception as e:
            logger.error(f"Direct SQL delete failed: {str(e)}")
            return False

# Create a singleton instance for easy access
db = DatabaseFacade()