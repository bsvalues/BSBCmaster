"""
This module provides database connection and SQL query execution functionality.
It handles parameter extraction, query validation, and secure execution against
PostgreSQL and MSSQL databases.
"""

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import psycopg2
import psycopg2.extras
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.validators import (DANGEROUS_KEYWORDS, SQL_INJECTION_PATTERNS,
                           validate_query, validate_query_parameters)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy base class
Base = declarative_base()


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


def create_db_engine(db: str = "postgres"):
    """
    Create SQLAlchemy engine for the specified database.
    
    Args:
        db: The database type ('postgres' or 'mssql')
        
    Returns:
        Engine: SQLAlchemy engine object
    """
    conn_string = get_connection_string(db)
    engine = create_engine(
        conn_string,
        pool_pre_ping=True,
        pool_recycle=300
    )
    return engine


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


def convert_param_style(query: str, params: Union[List[Any], Dict[str, Any]], param_style: str) -> Tuple[str, Union[List[Any], Dict[str, Any]]]:
    """
    Convert between different SQL parameter styles.
    
    Args:
        query: SQL query string
        params: Query parameters (list or dict)
        param_style: Parameter style ('named', 'qmark', 'format', 'numeric')
        
    Returns:
        Tuple containing:
            - The SQL query with appropriate parameter style
            - Parameters in the appropriate format
    """
    if param_style == "named":  # :param style
        # If params is a list, convert to a dict with autogenerated parameter names
        if isinstance(params, list):
            named_params = {f"p{i}": val for i, val in enumerate(params)}
            query_with_named = query
            for i, _ in enumerate(params):
                query_with_named = query_with_named.replace("?", f":p{i}", 1)
            return query_with_named, named_params
        # For PostgreSQL, convert :param to %(param)s
        converted_query = query
        for param_name in params.keys():
            pattern = rf':({param_name})\b'
            converted_query = re.sub(pattern, r'%(\1)s', converted_query)
        return converted_query, params
        
    elif param_style == "qmark":  # ? style
        if isinstance(params, dict):
            # Extract parameter names in order of appearance in the query
            param_names = []
            for param_name in params.keys():
                pattern = rf':({param_name})\b'
                if re.search(pattern, query):
                    param_names.append(param_name)
                    
            # Convert to positional parameters
            positional_params = [params[name] for name in param_names]
            query_with_qmarks = query
            for param_name in param_names:
                query_with_qmarks = query_with_qmarks.replace(f":{param_name}", "?", 1)
            return query_with_qmarks, positional_params
        return query, params
        
    elif param_style == "format":  # %s style
        if isinstance(params, dict):
            # Similar to named, but converting to %s format for psycopg2
            positional_params = []
            # Extract parameter names in order of appearance
            for param_name in params.keys():
                pattern = rf':({param_name})\b'
                matches = re.findall(pattern, query)
                positional_params.extend([params[param_name]] * len(matches))
            
            # Replace named parameters with %s
            converted_query = query
            for param_name in params.keys():
                pattern = rf':({param_name})\b'
                converted_query = re.sub(pattern, '%s', converted_query)
            return converted_query, positional_params
        # For PostgreSQL, leave as %s format
        return query, params
        
    elif param_style == "numeric":  # :1, :2, etc. style
        if isinstance(params, list):
            # Convert list to numeric style
            converted_query = query
            for i, _ in enumerate(params):
                converted_query = converted_query.replace("?", f":{i+1}", 1)
            return converted_query, params
        # If dict, convert to list based on numeric placeholders
        numeric_params = []
        max_param_num = 0
        # Find the highest parameter number
        for match in re.finditer(r':(\d+)', query):
            param_num = int(match.group(1))
            max_param_num = max(max_param_num, param_num)
            
        # Create a list with the right size
        numeric_params = [None] * max_param_num
        # Fill in values from dict
        for param_name, value in params.items():
            if param_name.isdigit():
                numeric_params[int(param_name) - 1] = value
                
        return query, numeric_params
    
    return query, params


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
            engine = create_db_engine(db)
            
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
                    result = connection.execute(text(query), **params)
                    
                    # Process results
                    rows = [dict(row) for row in result]
                    
                    # Execute count query if needed
                    total_records = len(rows)
                    total_pages = 1
                    
                    if count_query:
                        try:
                            count_result = connection.execute(text(count_query), **params)
                            if count_result:
                                row = count_result.fetchone()
                                if row and hasattr(row, 'total_count'):
                                    total_records = row.total_count
                                    total_pages = (total_records + page_size - 1) // page_size
                        except Exception as e:
                            logger.warning(f"Count query failed: {str(e)}, using result count instead")
                    
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
                        "columns": result.keys() if result else []
                    }
                    
                elif isinstance(params, list):
                    # For positional parameters in MSSQL
                    # Replace ? with positional parameters
                    formatted_query = query
                    for i in range(formatted_query.count('?')):
                        formatted_query = formatted_query.replace('?', f':p{i}', 1)
                    
                    query = formatted_query
                    
                    # Convert list to dict for SQLAlchemy
                    param_dict = {f"p{i}": val for i, val in enumerate(params)}
                    
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
                    result = connection.execute(text(query), **param_dict)
                    
                    # Process results
                    rows = [dict(row) for row in result]
                    
                    # Execute count query if needed
                    total_records = len(rows)
                    total_pages = 1
                    
                    if count_query:
                        try:
                            count_result = connection.execute(text(count_query), **param_dict)
                            if count_result:
                                row = count_result.fetchone()
                                if row and hasattr(row, 'total_count'):
                                    total_records = row.total_count
                                    total_pages = (total_records + page_size - 1) // page_size
                        except Exception as e:
                            logger.warning(f"Count query failed: {str(e)}, using result count instead")
                    
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
                        "columns": result.keys() if result else []
                    }
        
        # Unsupported database type
        return {
            "status": "error",
            "message": f"Unsupported database type: {db}",
            "execution_time": time.time() - start_time
        }
        
    except Exception as e:
        logger.error(f"Error executing query with explicit params: {str(e)}")
        return {
            "status": "error",
            "message": f"Query execution failed: {str(e)}",
            "execution_time": time.time() - start_time
        }


def execute_parameterized_query(db: str, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None, 
                              param_style: str = "format", page: int = 1, page_size: Optional[int] = None,
                              security_level: str = "medium") -> Dict[str, Any]:
    """
    Execute a parameterized SQL query with security validation and pagination.
    
    Args:
        db: Database type ('postgres' or 'mssql')
        query: SQL query to execute
        params: Query parameters (list or dict)
        param_style: Parameter style ('named', 'qmark', 'format', 'numeric')
        page: Page number for pagination (1-based)
        page_size: Number of records per page (None for all)
        security_level: Security validation level ('high', 'medium', 'low', 'none')
        
    Returns:
        Dict containing:
            - status: 'success' or 'error'
            - data: List of result records as dictionaries
            - execution_time: Time taken to execute the query
            - pagination: Pagination metadata
                - page: Current page number
                - page_size: Number of records per page
                - total_records: Total number of records
                - total_pages: Total number of pages
                - has_next: Whether there is a next page
                - has_prev: Whether there is a previous page
    """
    start_time = time.time()
    
    try:
        # Validate query for security vulnerabilities
        if security_level != "none":
            validation_result = validate_query(query, security_level)
            if not validation_result["is_safe"]:
                return {
                    "status": "error",
                    "message": f"Query validation failed: {validation_result['reason']}",
                    "execution_time": time.time() - start_time
                }
        
        # Convert parameter style if needed
        if params:
            query, params = convert_param_style(query, params, param_style)
            
            # Validate parameters
            param_validation_result = validate_query_parameters(params)
            if not param_validation_result["is_valid"]:
                return {
                    "status": "error",
                    "message": f"Parameter validation failed: {param_validation_result['reason']}",
                    "execution_time": time.time() - start_time
                }
        
        # Add pagination if page_size is specified
        original_query = query
        count_query = None
        
        if page_size:
            # For PostgreSQL
            if db == "postgres":
                # Create a count query to get total records
                count_query = f"SELECT COUNT(*) AS total_count FROM ({original_query}) AS count_subquery"
                
                # Add pagination to the original query
                offset = (page - 1) * page_size
                query = f"{original_query} LIMIT {page_size} OFFSET {offset}"
            
            # For MSSQL (using SQL Server 2012+ pagination)
            elif db == "mssql":
                # Need to make sure the query has an ORDER BY clause for OFFSET/FETCH
                if "ORDER BY" not in query.upper():
                    # Add a default ORDER BY on the first column
                    query = f"{query} ORDER BY 1"
                
                # Add pagination
                offset = (page - 1) * page_size
                query = f"{query} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                
                # Create a count query
                count_query = f"SELECT COUNT(*) AS total_count FROM ({original_query}) AS count_subquery"
                
        # Execute query using the appropriate database driver
        if db == "postgres":
            # Prepare connection
            conn_string = get_connection_string(db)
            
            # Strip sqlalchemy prefix if present
            if conn_string.startswith('postgresql://'):
                conn_string = conn_string.replace('postgresql://', '')
            elif conn_string.startswith('postgresql+psycopg2://'):
                conn_string = conn_string.replace('postgresql+psycopg2://', '')
                
            # Create connection
            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Execute the query
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Fetch results
                results = cursor.fetchall()
                
                # Get the column names
                column_names = [desc[0] for desc in cursor.description]
                
                # Execute count query if pagination is enabled
                total_records = None
                total_pages = None
                
                if count_query:
                    cursor.execute(count_query, params)
                    count_result = cursor.fetchone()
                    total_records = count_result["total_count"]
                    total_pages = (total_records + page_size - 1) // page_size
                
            finally:
                cursor.close()
                conn.close()
            
        elif db == "mssql":
            # Use SQLAlchemy for MSSQL
            engine = create_db_engine(db)
            with engine.connect() as connection:
                # Execute the main query
                if params:
                    if isinstance(params, list):
                        result = connection.execute(text(query), params)
                    else:
                        result = connection.execute(text(query), **params)
                else:
                    result = connection.execute(text(query))
                
                # Fetch results
                results = [dict(row) for row in result]
                
                # Execute count query if pagination is enabled
                total_records = None
                total_pages = None
                
                if count_query:
                    if params:
                        if isinstance(params, list):
                            count_result = connection.execute(text(count_query), params)
                        else:
                            count_result = connection.execute(text(count_query), **params)
                    else:
                        count_result = connection.execute(text(count_query))
                    
                    total_records = count_result.fetchone()[0]
                    total_pages = (total_records + page_size - 1) // page_size
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Prepare pagination metadata
        pagination = None
        if page_size:
            pagination = {
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages if total_pages else False,
                "has_prev": page > 1
            }
        
        # Return results
        return {
            "status": "success",
            "data": results,
            "execution_time": execution_time,
            "pagination": pagination
        }
        
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return {
            "status": "error",
            "message": f"Query execution failed: {str(e)}",
            "execution_time": time.time() - start_time
        }


# This has been moved to app/nl_processing.py for better organization.
# Importing the function here to maintain backward compatibility.
from app.nl_processing import sql_to_natural_language