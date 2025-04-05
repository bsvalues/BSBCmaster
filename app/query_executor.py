"""
This module provides functionality for executing SQL queries against the database.
"""

import logging
import re
import time
from typing import Dict, List, Any, Tuple, Optional, Union

import psycopg2
import psycopg2.extras
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.db import get_pg_connection, close_pg_connection
from app.models import ParameterizedSQLQuery, SQLQuery, QueryResult

# Configure logging
logger = logging.getLogger(__name__)

# Dangerous SQL patterns to check for in queries
DANGEROUS_PATTERNS = [
    r"DROP\s+DATABASE",
    r"DROP\s+TABLE",
    r"DROP\s+SCHEMA",
    r"TRUNCATE\s+TABLE",
    r"DELETE\s+FROM\s+\w+\s+(?!WHERE)",  # DELETE without WHERE
    r"UPDATE\s+\w+\s+SET\s+(?!WHERE)",   # UPDATE without WHERE
    r"CREATE\s+USER",
    r"ALTER\s+USER",
    r"GRANT\s+",
    r"REVOKE\s+",
    r"EXECUTE\s+AS",
    r";.*SELECT",  # Multiple statements
    r";.*INSERT",
    r";.*UPDATE",
    r";.*DELETE",
    r";.*DROP",
    r";.*CREATE",
    r";.*ALTER",
    r"SELECT\s+INTO\s+(?:OUTFILE|DUMPFILE)",
    r"LOAD\s+DATA\s+(?:LOCAL\s+)?INFILE",
    r"INFORMATION_SCHEMA\.(?:TABLES|COLUMNS)",
    r"pg_catalog\.",
    r"sys\.",
    r"msdb\.",
    r"master\.",
    r"xp_cmdshell",
    r"sp_execute",
    r"EXEC\s+sp_",
    r"EXECUTE\s+sp_"
]

DANGEROUS_PATTERN_REGEX = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)

def is_dangerous_query(query: str) -> bool:
    """
    Check if a query contains dangerous patterns.
    
    Args:
        query: The SQL query to check
        
    Returns:
        bool: True if the query contains dangerous patterns, False otherwise
    """
    return bool(DANGEROUS_PATTERN_REGEX.search(query))

def get_query_type(query: str) -> str:
    """
    Determine the type of SQL query (SELECT, INSERT, UPDATE, DELETE, etc.).
    
    Args:
        query: The SQL query to check
        
    Returns:
        str: The query type
    """
    query = query.strip().upper()
    
    if query.startswith("SELECT"):
        return "SELECT"
    elif query.startswith("INSERT"):
        return "INSERT"
    elif query.startswith("UPDATE"):
        return "UPDATE"
    elif query.startswith("DELETE"):
        return "DELETE"
    elif query.startswith("CREATE"):
        return "CREATE"
    elif query.startswith("ALTER"):
        return "ALTER"
    elif query.startswith("DROP"):
        return "DROP"
    else:
        return "UNKNOWN"

def format_query_params(query: str, params: Union[Dict[str, Any], List[Any]], db_type: str) -> Tuple[str, Union[Dict[str, Any], List[Any]]]:
    """
    Format query parameters based on database type.
    
    Args:
        query: The SQL query with placeholders
        params: The query parameters
        db_type: The database type (postgres, mssql)
        
    Returns:
        Tuple[str, Union[Dict[str, Any], List[Any]]]: The formatted query and parameters
    """
    if db_type == "postgres":
        # If using a list of parameters, convert to using PostgreSQL placeholders
        if isinstance(params, list):
            # Replace ? with %s for PostgreSQL
            formatted_query = re.sub(r'\?', '%s', query)
            return formatted_query, params
            
        # If using a dict of parameters, convert to using named placeholders
        elif isinstance(params, dict):
            formatted_query = query
            
            # Check for different parameter styles
            # Handle :param style (convert to %(param)s)
            for param_name in params.keys():
                # Look for exact matches of :param_name (not partial matches)
                pattern = r':(' + param_name + r')\b'
                formatted_query = re.sub(pattern, r'%(\1)s', formatted_query)
            
            # Handle @param style (sometimes used in SQL Server)
            for param_name in params.keys():
                pattern = r'@(' + param_name + r')\b'
                formatted_query = re.sub(pattern, r'%(\1)s', formatted_query)
                
            return formatted_query, params
        
        # Return unmodified if params is None or another type
        return query, params if params is not None else {}
        
    elif db_type == "mssql":
        # For MSSQL, handle parameter conversion
        if isinstance(params, list):
            # ? placeholders are the native style for pyodbc
            return query, params
            
        # For MSSQL with dict parameters, convert to ordered list
        elif isinstance(params, dict):
            # Use regex to find all named parameters in the query
            # This matches both :param and @param styles
            param_matches = re.findall(r'[:@](\w+)', query)
            
            # Create ordered parameter list based on occurrence in query
            ordered_params = []
            param_map = {}  # Track parameter positions
            
            # Build an ordered list of parameters
            for param_name in param_matches:
                if param_name in params:
                    # If we've already processed this parameter, skip it
                    if param_name in param_map:
                        continue
                        
                    # Add parameter to ordered list
                    ordered_params.append(params[param_name])
                    param_map[param_name] = len(ordered_params) - 1
            
            # Replace named parameters with ? placeholders
            formatted_query = query
            for param_name in param_map:
                # Replace both :param and @param styles
                formatted_query = re.sub(r'[:@]' + param_name + r'\b', '?', formatted_query)
                
            return formatted_query, ordered_params
    
    # Default case - return unmodified
    return query, params if params is not None else {}

def paginate_results(data: List[Dict[str, Any]], page: int, page_size: int, total_count: int) -> Dict[str, Any]:
    """
    Paginate query results.
    
    Args:
        data: The query results
        page: The page number
        page_size: The page size
        total_count: The total number of records
        
    Returns:
        Dict[str, Any]: Pagination metadata
    """
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    
    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_count,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "next_page": page + 1 if page < total_pages else None,
        "prev_page": page - 1 if page > 1 else None
    }

async def execute_parameterized_query(payload: ParameterizedSQLQuery, allow_write: bool = False) -> Dict[str, Any]:
    """
    Execute a parameterized SQL query with enhanced security and error handling.
    
    Args:
        payload: The query payload
        allow_write: Whether to allow write operations (INSERT, UPDATE, DELETE)
        
    Returns:
        Dict[str, Any]: The query results
        
    Raises:
        HTTPException: If the query is unsafe or if a database error occurs
    """
    start_time = time.time()
    
    # Extract query parameters
    db_type = payload.db.value
    query = payload.query
    params = payload.params if payload.params is not None else {}
    param_style = payload.param_style.value
    page = payload.page
    page_size = payload.page_size
    
    logger.info(f"Executing parameterized query on {db_type} with {len(params)} params")
    
    # Check for dangerous patterns
    if is_dangerous_query(query) and not allow_write:
        logger.warning(f"Dangerous query pattern detected: {query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Query contains potentially dangerous operations"
        )
    
    # Check if query is a SELECT query for read-only mode
    query_type = get_query_type(query)
    if query_type not in ["SELECT"] and not allow_write:
        logger.warning(f"Non-SELECT query detected: {query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Only SELECT queries are allowed in read-only mode. Found: {query_type}"
        )
    
    # Format query and parameters based on database type
    formatted_query, formatted_params = format_query_params(query, params, db_type)
    
    try:
        if db_type == "postgres":
            # Get PostgreSQL connection
            conn = get_pg_connection()
            
            try:
                # Create count query for pagination
                count_query = None
                
                if query_type == "SELECT" and page_size:
                    # Extract the FROM part and beyond
                    from_part_match = re.search(r'\bFROM\b.*', formatted_query, re.IGNORECASE | re.DOTALL)
                    
                    if from_part_match:
                        from_part = from_part_match.group(0)
                        
                        # Remove any ORDER BY, LIMIT, OFFSET clauses for count
                        from_part = re.sub(r'\bORDER\s+BY\b.*', '', from_part, flags=re.IGNORECASE | re.DOTALL)
                        from_part = re.sub(r'\bLIMIT\b.*', '', from_part, flags=re.IGNORECASE | re.DOTALL)
                        from_part = re.sub(r'\bOFFSET\b.*', '', from_part, flags=re.IGNORECASE | re.DOTALL)
                        
                        count_query = f"SELECT COUNT(*) AS count {from_part}"
                
                # Create cursor with column names
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Execute count query if available
                    total_count = 0
                    if count_query:
                        try:
                            cursor.execute(count_query, formatted_params)
                            count_result = cursor.fetchone()
                            total_count = int(count_result["count"]) if count_result and "count" in count_result else 0
                        except Exception as e:
                            logger.warning(f"Count query failed, pagination may be incomplete: {str(e)}")
                            # Continue with main query even if count fails
                    
                    # Add LIMIT and OFFSET for pagination
                    if page_size and "LIMIT" not in formatted_query.upper():
                        offset = (page - 1) * page_size
                        paginated_query = f"{formatted_query} LIMIT {page_size} OFFSET {offset}"
                    else:
                        paginated_query = formatted_query
                    
                    # Execute main query
                    cursor.execute(paginated_query, formatted_params)
                    
                    # Fetch results
                    results = cursor.fetchall()
                    
                    # Get column names and types
                    columns = {}
                    if cursor.description:
                        for desc in cursor.description:
                            col_name = desc.name
                            col_type = desc.type_code
                            columns[col_name] = str(col_type)
                    
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    
                    # Create pagination metadata
                    pagination = paginate_results(results, page, page_size, total_count)
                    
                    # Convert results to list of dicts
                    converted_results = []
                    for row in results:
                        converted_row = {}
                        for key, value in row.items():
                            converted_row[key] = value
                        converted_results.append(converted_row)
                    
                    return {
                        "status": "success",
                        "data": converted_results,
                        "execution_time": execution_time,
                        "pagination": pagination,
                        "column_types": columns
                    }
            finally:
                close_pg_connection(conn)
        elif db_type == "mssql":
            try:
                import pyodbc
                from app.db import get_connection_string
                
                # Get MSSQL connection string from environment
                conn_string = get_connection_string("mssql")
                
                # Convert SQLAlchemy connection string to pyodbc format if needed
                if "mssql+pyodbc" in conn_string:
                    # Extract components
                    parts = conn_string.replace("mssql+pyodbc://", "").split("/")
                    if len(parts) >= 2:
                        auth_part = parts[0]  # username:password@server
                        db_part = parts[1].split("?")[0]  # database
                        
                        # Extract username, password, server
                        auth_components = auth_part.split("@")
                        if len(auth_components) == 2:
                            credentials = auth_components[0].split(":")
                            if len(credentials) == 2:
                                username = credentials[0]
                                password = credentials[1]
                                server = auth_components[1]
                                
                                # Create pyodbc connection string
                                conn_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_part};UID={username};PWD={password}"
                
                # Connect to MSSQL
                conn = pyodbc.connect(conn_string)
                
                try:
                    # Format parameters based on style
                    formatted_query = query
                    formatted_params = params
                    
                    # Create cursor
                    cursor = conn.cursor()
                    
                    # For pagination, we need count query
                    count_query = None
                    total_count = 0
                    
                    if page_size:
                        # Extract the base query (before any ORDER BY, OFFSET, etc.)
                        base_query = re.sub(r'\bORDER\s+BY\b.*', '', formatted_query, flags=re.IGNORECASE | re.DOTALL)
                        base_query = re.sub(r'\bOFFSET\b.*', '', base_query, flags=re.IGNORECASE | re.DOTALL)
                        base_query = re.sub(r'\bFETCH\b.*', '', base_query, flags=re.IGNORECASE | re.DOTALL)
                        
                        # Create count query
                        count_query = f"SELECT COUNT(*) AS total_count FROM ({base_query}) AS count_subquery"
                        
                        # Execute count query
                        try:
                            cursor.execute(count_query, formatted_params)
                            count_result = cursor.fetchone()
                            if count_result:
                                total_count = count_result[0]
                        except Exception as e:
                            logger.warning(f"Count query failed, pagination may be incomplete: {str(e)}")
                        
                        # Make sure we have an ORDER BY for OFFSET/FETCH
                        if "ORDER BY" not in formatted_query.upper():
                            formatted_query = f"{formatted_query} ORDER BY 1"
                        
                        # Add pagination
                        offset = (page - 1) * page_size
                        paginated_query = f"{formatted_query} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                        formatted_query = paginated_query
                    
                    # Execute main query
                    cursor.execute(formatted_query, formatted_params)
                    
                    # Get column names
                    columns = {}
                    if cursor.description:
                        for i, column in enumerate(cursor.description):
                            col_name = column[0]
                            col_type = column[1].__name__ if column[1] else "unknown"
                            columns[col_name] = col_type
                    
                    # Fetch results
                    rows = cursor.fetchall()
                    
                    # Convert to list of dicts
                    results = []
                    for row in rows:
                        result_dict = {}
                        for i, column in enumerate(cursor.description):
                            # Handle different data types
                            value = row[i]
                            if isinstance(value, (datetime, bytearray, bytes)):
                                # Convert to string for serialization
                                value = str(value)
                            result_dict[column[0]] = value
                        results.append(result_dict)
                    
                    # Create pagination metadata
                    pagination = paginate_results(results, page, page_size, total_count)
                    
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    
                    return {
                        "status": "success",
                        "data": results,
                        "execution_time": execution_time,
                        "pagination": pagination,
                        "column_types": columns
                    }
                finally:
                    # Close cursor and connection
                    if 'cursor' in locals():
                        cursor.close()
                    conn.close()
            except ImportError as e:
                logger.error(f"Missing dependencies for MSSQL support: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="MSSQL support requires pyodbc, which is not installed"
                )
            except Exception as e:
                logger.error(f"MSSQL error executing query: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"MSSQL error: {str(e)}"
                )
        else:
            # Unsupported database type
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Database type {db_type} not implemented yet"
            )
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error executing query: {str(e)}")
        
        # Format error message
        error_message = str(e)
        # Sanitize error message to avoid exposing sensitive information
        if "permission denied" in error_message.lower():
            error_message = "Permission denied for the requested operation"
        elif "does not exist" in error_message.lower():
            # Extract table or column name if possible
            match = re.search(r'(table|column|relation) "(.*?)" does not exist', error_message, re.IGNORECASE)
            if match:
                obj_type, obj_name = match.groups()
                error_message = f"{obj_type.capitalize()} '{obj_name}' does not exist"
            else:
                error_message = "Referenced object does not exist"
        
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Database error: {error_message}"
        )
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {str(e)}"
        )

def extract_schema_info(db_type: str) -> Dict[str, Any]:
    """
    Extract schema information from the database.
    
    Args:
        db_type: The database type
        
    Returns:
        Dict[str, Any]: The schema information
        
    Raises:
        HTTPException: If a database error occurs
    """
    start_time = time.time()
    
    try:
        if db_type == "postgres":
            # Get PostgreSQL connection
            conn = get_pg_connection()
            
            try:
                # Define PostgreSQL schema query
                schema_query = """
                SELECT 
                    c.table_schema,
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    CASE WHEN c.is_nullable = 'YES' THEN true ELSE false END as is_nullable,
                    c.column_default,
                    CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                    CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END as is_foreign_key,
                    fk.foreign_table_name as referenced_table_name,
                    fk.foreign_column_name as referenced_column_name,
                    col_description(pgc.oid, c.ordinal_position) as description
                FROM 
                    information_schema.columns c
                LEFT JOIN 
                    pg_class pgc ON pgc.relname = c.table_name
                LEFT JOIN (
                    SELECT 
                        tc.table_schema, 
                        tc.table_name, 
                        kcu.column_name 
                    FROM 
                        information_schema.table_constraints tc
                    JOIN 
                        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE 
                        tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.table_schema = pk.table_schema AND c.table_name = pk.table_name AND c.column_name = pk.column_name
                LEFT JOIN (
                    SELECT 
                        kcu.table_schema, 
                        kcu.table_name, 
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM 
                        information_schema.table_constraints tc
                    JOIN 
                        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    JOIN 
                        information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    WHERE 
                        tc.constraint_type = 'FOREIGN KEY'
                ) fk ON c.table_schema = fk.table_schema AND c.table_name = fk.table_name AND c.column_name = fk.column_name
                WHERE 
                    c.table_schema = 'public'
                ORDER BY 
                    c.table_name, c.ordinal_position;
                """
                
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Execute schema query
                    cursor.execute(schema_query)
                    rows = cursor.fetchall()
                    
                    # Process results
                    schema_items = []
                    tables_dict = {}
                    
                    for row in rows:
                        # Create schema item
                        schema_item = {
                            "table_name": row["table_name"],
                            "column_name": row["column_name"],
                            "data_type": row["data_type"],
                            "is_nullable": row["is_nullable"],
                            "column_default": row["column_default"],
                            "is_primary_key": row.get("is_primary_key", False),
                            "is_foreign_key": row.get("is_foreign_key", False),
                            "references_table": row.get("referenced_table_name"),
                            "references_column": row.get("referenced_column_name"),
                            "description": row.get("description")
                        }
                        schema_items.append(schema_item)
                        
                        # Add to tables dictionary
                        table_name = row["table_name"]
                        if table_name not in tables_dict:
                            tables_dict[table_name] = {
                                "name": table_name,
                                "description": None,
                                "columns": [],
                                "primary_keys": [],
                                "foreign_keys": {},
                                "row_count": None
                            }
                        
                        # Add column to table
                        tables_dict[table_name]["columns"].append(schema_item)
                        
                        # Add primary key if applicable
                        if row.get("is_primary_key", False):
                            tables_dict[table_name]["primary_keys"].append(row["column_name"])
                        
                        # Add foreign key if applicable
                        if row.get("is_foreign_key", False):
                            tables_dict[table_name]["foreign_keys"][row["column_name"]] = {
                                "references_table": row["referenced_table_name"],
                                "references_column": row["referenced_column_name"]
                            }
                    
                    # Get row counts for each table
                    table_names = list(tables_dict.keys())
                    for table_name in table_names:
                        try:
                            cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
                            count_result = cursor.fetchone()
                            if count_result and "count" in count_result:
                                tables_dict[table_name]["row_count"] = int(count_result["count"])
                        except Exception as e:
                            logger.warning(f"Could not get row count for table {table_name}: {str(e)}")
            finally:
                close_pg_connection(conn)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "db_schema": schema_items,
                "tables": list(tables_dict.values()),
                "execution_time": execution_time
            }
        elif db_type == "mssql":
            try:
                import pyodbc
                from app.db import get_connection_string
                
                # Get MSSQL connection string from environment
                conn_string = get_connection_string("mssql")
                
                # Connect to MSSQL using pyodbc
                # Convert SQLAlchemy connection string to pyodbc format if needed
                if "mssql+pyodbc" in conn_string:
                    # Extract components
                    parts = conn_string.replace("mssql+pyodbc://", "").split("/")
                    if len(parts) >= 2:
                        auth_part = parts[0]  # username:password@server
                        db_part = parts[1].split("?")[0]  # database
                        
                        # Extract username, password, server
                        auth_components = auth_part.split("@")
                        if len(auth_components) == 2:
                            credentials = auth_components[0].split(":")
                            if len(credentials) == 2:
                                username = credentials[0]
                                password = credentials[1]
                                server = auth_components[1]
                                
                                # Create pyodbc connection string
                                conn_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_part};UID={username};PWD={password}"
                
                # Connect to MSSQL
                conn = pyodbc.connect(conn_string)
                
                try:
                    cursor = conn.cursor()
                    
                    # Get table information
                    schema_items = []
                    tables_dict = {}
                    
                    # Query for tables, columns, and their properties
                    schema_query = """
                    SELECT 
                        t.TABLE_SCHEMA as table_schema,
                        t.TABLE_NAME as table_name,
                        c.COLUMN_NAME as column_name,
                        c.DATA_TYPE as data_type,
                        CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END as is_nullable,
                        c.COLUMN_DEFAULT as column_default,
                        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_primary_key,
                        CASE WHEN fk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_foreign_key,
                        fk.REFERENCED_TABLE_NAME as referenced_table_name,
                        fk.REFERENCED_COLUMN_NAME as referenced_column_name,
                        ep.value as description
                    FROM 
                        INFORMATION_SCHEMA.TABLES t
                    JOIN 
                        INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
                    LEFT JOIN (
                        SELECT 
                            ku.TABLE_SCHEMA,
                            ku.TABLE_NAME,
                            ku.COLUMN_NAME
                        FROM 
                            INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN 
                            INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                        WHERE 
                            tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA AND c.TABLE_NAME = pk.TABLE_NAME AND c.COLUMN_NAME = pk.COLUMN_NAME
                    LEFT JOIN (
                        SELECT 
                            ku1.TABLE_SCHEMA,
                            ku1.TABLE_NAME,
                            ku1.COLUMN_NAME,
                            ku2.TABLE_NAME AS REFERENCED_TABLE_NAME,
                            ku2.COLUMN_NAME AS REFERENCED_COLUMN_NAME
                        FROM 
                            INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                        JOIN 
                            INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku1 ON rc.CONSTRAINT_NAME = ku1.CONSTRAINT_NAME
                        JOIN 
                            INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku2 ON rc.UNIQUE_CONSTRAINT_NAME = ku2.CONSTRAINT_NAME
                    ) fk ON c.TABLE_SCHEMA = fk.TABLE_SCHEMA AND c.TABLE_NAME = fk.TABLE_NAME AND c.COLUMN_NAME = fk.COLUMN_NAME
                    LEFT JOIN 
                        sys.extended_properties ep ON OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME) = ep.major_id 
                        AND c.ORDINAL_POSITION = ep.minor_id 
                        AND ep.name = 'MS_Description'
                    WHERE 
                        t.TABLE_TYPE = 'BASE TABLE'
                        AND t.TABLE_SCHEMA = 'dbo'
                    ORDER BY 
                        t.TABLE_NAME, c.ORDINAL_POSITION;
                    """
                    
                    cursor.execute(schema_query)
                    
                    # Process results
                    for row in cursor.fetchall():
                        schema_item = {
                            "table_name": row.table_name,
                            "column_name": row.column_name,
                            "data_type": row.data_type,
                            "is_nullable": bool(row.is_nullable),
                            "column_default": row.column_default,
                            "is_primary_key": bool(row.is_primary_key),
                            "is_foreign_key": bool(row.is_foreign_key),
                            "references_table": row.referenced_table_name,
                            "references_column": row.referenced_column_name,
                            "description": row.description
                        }
                        schema_items.append(schema_item)
                        
                        # Add to tables dictionary
                        table_name = row.table_name
                        if table_name not in tables_dict:
                            tables_dict[table_name] = {
                                "name": table_name,
                                "description": None,
                                "columns": [],
                                "primary_keys": [],
                                "foreign_keys": {},
                                "row_count": None
                            }
                        
                        # Add column to table
                        tables_dict[table_name]["columns"].append(schema_item)
                        
                        # Add primary key if applicable
                        if bool(row.is_primary_key):
                            tables_dict[table_name]["primary_keys"].append(row.column_name)
                        
                        # Add foreign key if applicable
                        if bool(row.is_foreign_key):
                            tables_dict[table_name]["foreign_keys"][row.column_name] = {
                                "references_table": row.referenced_table_name,
                                "references_column": row.referenced_column_name
                            }
                    
                    # Get row counts for each table
                    for table_name in tables_dict.keys():
                        try:
                            cursor.execute(f"SELECT COUNT(*) AS count FROM [{table_name}]")
                            count_result = cursor.fetchone()
                            if count_result:
                                tables_dict[table_name]["row_count"] = count_result.count
                        except Exception as e:
                            logger.warning(f"Could not get row count for table {table_name}: {str(e)}")
                    
                    # Get table descriptions
                    table_desc_query = """
                    SELECT 
                        t.name AS table_name,
                        ep.value AS description
                    FROM 
                        sys.tables t
                    LEFT JOIN 
                        sys.extended_properties ep ON t.object_id = ep.major_id 
                        AND ep.minor_id = 0 
                        AND ep.name = 'MS_Description'
                    WHERE 
                        t.schema_id = SCHEMA_ID('dbo')
                    """
                    
                    cursor.execute(table_desc_query)
                    for row in cursor.fetchall():
                        if row.table_name in tables_dict:
                            tables_dict[row.table_name]["description"] = row.description
                
                finally:
                    # Close cursor and connection
                    if 'cursor' in locals():
                        cursor.close()
                    conn.close()
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "db_schema": schema_items,
                    "tables": list(tables_dict.values()),
                    "execution_time": execution_time
                }
                
            except ImportError as e:
                logger.error(f"Missing dependencies for MSSQL schema discovery: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="MSSQL support requires pyodbc, which is not installed"
                )
            except Exception as e:
                logger.error(f"MSSQL error getting schema: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"MSSQL schema discovery error: {str(e)}"
                )
        else:
            # Unsupported database type
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Database type {db_type} not implemented yet"
            )
    except Exception as e:
        logger.error(f"Error getting database schema: {str(e)}")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "status": "error",
            "message": f"Error getting database schema: {str(e)}",
            "db_schema": [],
            "tables": [],
            "execution_time": execution_time
        }