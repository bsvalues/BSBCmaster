"""
This module provides database utility functions for the MCP Assessor Agent API.
It is a copy of the necessary functions from the original db.py module to avoid circular imports.
"""

import os
import logging
import re
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import psycopg2
import psycopg2.extras
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection_string(db: str = "postgres") -> str:
    """
    Get database connection string from environment variables.
    
    Args:
        db: The database type ('postgres' or 'mssql')
        
    Returns:
        str: Database connection string
    """
    if db == "postgres":
        # Use the DATABASE_URL environment variable
        conn_string = current_app.config.get("SQLALCHEMY_DATABASE_URI")
        if not conn_string:
            raise ValueError("DATABASE_URL environment variable not set")
        return conn_string
    elif db == "mssql":
        # Construct MSSQL connection string from environment variables
        from os import environ
        server = environ.get("MSSQL_SERVER")
        database = environ.get("MSSQL_DATABASE")
        username = environ.get("MSSQL_USERNAME")
        password = environ.get("MSSQL_PASSWORD")
        
        if not all([server, database, username, password]):
            raise ValueError("MSSQL environment variables not set")
            
        return f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {db}")


def parse_for_parameters(sql_query: str) -> Tuple[str, List[Any]]:
    """
    Extract parameters from a SQL query and replace them with placeholders.
    
    Args:
        sql_query: The SQL query to parse
        
    Returns:
        Tuple containing:
            - The SQL query with string literals replaced by placeholders
            - List of extracted parameter values
    """
    # Regular expressions for different types of literals
    string_pattern = r"'([^'\\]*(\\.[^'\\]*)*)'"  # Matches string literals with proper escape handling
    numeric_pattern = r"\b(\d+\.?\d*)\b"  # Matches numeric literals
    
    # Extract and replace string literals
    string_params = re.findall(string_pattern, sql_query)
    string_values = [match[0] for match in string_params]  # Extract the matched string values
    
    # Replace string literals with placeholders
    modified_query = sql_query
    for value in string_values:
        escaped_value = value.replace('\\', '\\\\').replace('.', '\\.').replace('+', '\\+')
        modified_query = re.sub(f"'{escaped_value}'", "%s", modified_query, 1)
    
    # Extract and replace numeric literals after WHERE, AND, OR, IN, etc.
    # This is a heuristic to avoid replacing table names, column references, etc.
    condition_keywords = r"\b(WHERE|AND|OR|IN|=|>|<|>=|<=|!=|<>|BETWEEN)\b"
    potential_params = []
    
    # Match all numbers following a condition keyword, allowing for whitespace
    number_matches = re.finditer(rf"{condition_keywords}\s+{numeric_pattern}", modified_query, re.IGNORECASE)
    
    for match in number_matches:
        keyword_end = match.start(2)  # End of the keyword
        number_start = match.start(3)  # Start of the number
        number_end = match.end(3)  # End of the number
        
        # Extract the number
        number_str = match.group(3)
        
        # Convert to appropriate type
        if "." in number_str:
            value = float(number_str)
        else:
            value = int(number_str)
        
        potential_params.append((number_start, number_end, value))
    
    # Sort in reverse order to avoid index shifting when replacing
    potential_params.sort(reverse=True)
    
    # Replace the numbers with placeholders
    for start, end, value in potential_params:
        modified_query = modified_query[:start] + "%s" + modified_query[end:]
        string_values.append(value)
    
    return modified_query, string_values


def execute_parameterized_query(db: str, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None, 
                               page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a SQL query with parameter extraction, validation, and proper execution.
    
    Args:
        db: Database type ('postgres' or 'mssql')
        query: SQL query to execute
        params: Optional query parameters (list or dict)
        page: Page number for pagination (1-based)
        page_size: Number of records per page (None for all)
        
    Returns:
        Dict containing:
            - status: 'success' or 'error'
            - data: List of result records as dictionaries
            - execution_time: Time taken to execute the query
            - pagination: Pagination metadata
    """
    start_time = time.time()
    
    try:
        # If no parameters provided, extract them from the query
        if params is None:
            modified_query, extracted_params = parse_for_parameters(query)
            return execute_query_with_explicit_params(db, modified_query, extracted_params, page, page_size)
        
        # If parameters are provided, use them directly
        return execute_query_with_explicit_params(db, query, params, page, page_size)
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        logger.error(f"Error executing query: {str(e)}")
        return {
            "status": "error",
            "message": f"Error executing query: {str(e)}",
            "execution_time": execution_time,
            "query": query
        }


def execute_query_with_explicit_params(db: str, query: str, params: Union[List[Any], Dict[str, Any]], 
                                    page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a SQL query with explicit parameter handling for different database types.
    This function provides specialized handling for various parameter styles and database types.
    
    Args:
        db: Database type ('postgres' or 'mssql')
        query: SQL query to execute
        params: Query parameters (list or dict)
        page: Page number for pagination (1-based)
        page_size: Number of records per page (None for all)
        
    Returns:
        Dict containing:
            - status: 'success' or 'error'
            - data: List of result records as dictionaries
            - execution_time: Time taken to execute the query
            - pagination: Pagination metadata
    """
    start_time = time.time()
    
    try:
        # Handle different database types
        if db.lower() == "postgres":
            # Get a PostgreSQL connection
            conn_string = get_connection_string(db)
            
            # Strip sqlalchemy prefix if present
            if conn_string.startswith('postgresql://'):
                conn_string = conn_string.replace('postgresql://', '')
            elif conn_string.startswith('postgresql+psycopg2://'):
                conn_string = conn_string.replace('postgresql+psycopg2://', '')
                
            # Create connection
            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            try:
                # Prepare parameters based on type
                if isinstance(params, dict):
                    # Convert named parameters for PostgreSQL
                    formatted_query = query
                    for param_name in params.keys():
                        # Convert :param to %(param)s style
                        pattern = rf':({param_name})\b'
                        formatted_query = re.sub(pattern, r'%(\1)s', formatted_query)
                        
                        # Also handle @param style
                        pattern = rf'@({param_name})\b'
                        formatted_query = re.sub(pattern, r'%(\1)s', formatted_query)
                        
                    query = formatted_query
                    
                elif isinstance(params, list):
                    # Convert qmark style (?) to %s for PostgreSQL
                    query = re.sub(r'\?', '%s', query)
                
                # Add pagination if needed
                original_query = query
                count_query = None
                
                if page_size:
                    # Create a count query to get total records
                    count_query = f"SELECT COUNT(*) AS total_count FROM ({original_query}) AS count_subquery"
                    
                    # Add LIMIT and OFFSET for pagination
                    offset = (page - 1) * page_size
                    query = f"{original_query} LIMIT {page_size} OFFSET {offset}"
                
                # Execute the query
                cursor.execute(query, params)
                
                # Fetch results
                results = cursor.fetchall()
                
                # Get column names
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Execute count query if pagination is enabled
                total_records = len(results)
                total_pages = 1
                
                if count_query:
                    try:
                        cursor.execute(count_query, params)
                        count_result = cursor.fetchone()
                        if count_result and "total_count" in count_result:
                            total_records = count_result["total_count"]
                            total_pages = (total_records + page_size - 1) // page_size
                    except Exception as e:
                        logger.warning(f"Count query failed: {str(e)}, using result count instead")
                
                # Prepare pagination metadata
                pagination = {
                    "page": page,
                    "page_size": page_size if page_size else len(results),
                    "total_records": total_records,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "data": results,
                    "execution_time": execution_time,
                    "pagination": pagination,
                    "columns": column_names
                }
                
            finally:
                cursor.close()
                conn.close()
                
        elif db.lower() == "mssql":
            # Use SQLAlchemy for MSSQL
            engine = create_engine(get_connection_string(db))
            
            with engine.connect() as connection:
                # Prepare parameters based on type
                if isinstance(params, dict):
                    # For named parameters in MSSQL, convert :param to @param
                    formatted_query = query
                    for param_name in params.keys():
                        pattern = rf':({param_name})\b'
                        formatted_query = re.sub(pattern, r'@\1', formatted_query)
                    
                    query = formatted_query
                    
                    # Add pagination if needed
                    original_query = query
                    count_query = None
                    
                    if page_size:
                        # Ensure there's an ORDER BY for OFFSET/FETCH
                        if "ORDER BY" not in query.upper():
                            query = f"{query} ORDER BY 1"
                            
                        # Create a count query
                        count_query = f"SELECT COUNT(*) AS total_count FROM ({original_query}) AS count_subquery"
                        
                        # Add pagination
                        offset = (page - 1) * page_size
                        query = f"{query} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                    
                    # Execute main query
                    result = connection.execute(text(query), params)
                    
                    # Process results
                    rows = [dict(row) for row in result]
                    
                    # Execute count query if needed
                    total_records = len(rows)
                    total_pages = 1
                    
                    if count_query:
                        try:
                            count_result = connection.execute(text(count_query), params).first()
                            if count_result and "total_count" in count_result:
                                total_records = count_result["total_count"]
                                total_pages = (total_records + page_size - 1) // page_size
                        except Exception as e:
                            logger.warning(f"Count query failed: {str(e)}, using result count instead")
                    
                    # Get column names
                    column_names = list(rows[0].keys()) if rows else []
                    
                elif isinstance(params, list):
                    # For positional parameters in MSSQL, convert to SQLAlchemy bindparam
                    # This is a simplified approach that assumes ?-style parameters
                    param_dict = {f"p{i}": val for i, val in enumerate(params)}
                    
                    # Replace ? with :p0, :p1, etc.
                    formatted_query = query
                    for i in range(len(params)):
                        formatted_query = formatted_query.replace('?', f":p{i}", 1)
                    
                    query = formatted_query
                    
                    # Add pagination if needed
                    original_query = query
                    count_query = None
                    
                    if page_size:
                        # Ensure there's an ORDER BY for OFFSET/FETCH
                        if "ORDER BY" not in query.upper():
                            query = f"{query} ORDER BY 1"
                            
                        # Create a count query
                        count_query = f"SELECT COUNT(*) AS total_count FROM ({original_query}) AS count_subquery"
                        
                        # Add pagination
                        offset = (page - 1) * page_size
                        query = f"{query} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                    
                    # Execute main query
                    result = connection.execute(text(query), param_dict)
                    
                    # Process results
                    rows = [dict(row) for row in result]
                    
                    # Execute count query if needed
                    total_records = len(rows)
                    total_pages = 1
                    
                    if count_query:
                        try:
                            count_result = connection.execute(text(count_query), param_dict).first()
                            if count_result and "total_count" in count_result:
                                total_records = count_result["total_count"]
                                total_pages = (total_records + page_size - 1) // page_size
                        except Exception as e:
                            logger.warning(f"Count query failed: {str(e)}, using result count instead")
                    
                    # Get column names
                    column_names = list(rows[0].keys()) if rows else []
                
                # Prepare pagination metadata
                pagination = {
                    "page": page,
                    "page_size": page_size if page_size else len(rows),
                    "total_records": total_records,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "data": rows,
                    "execution_time": execution_time,
                    "pagination": pagination,
                    "columns": column_names
                }
        
        else:
            raise ValueError(f"Unsupported database type: {db}")
            
    except Exception as e:
        execution_time = time.time() - start_time
        
        logger.error(f"Error executing query: {str(e)}")
        return {
            "status": "error",
            "message": f"Error executing query: {str(e)}",
            "execution_time": execution_time,
            "query": query
        }