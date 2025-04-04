import logging
import re
import pyodbc
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple, Union
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from .settings import settings

logger = logging.getLogger("mcp_assessor_api")

# Global connection pool for PostgreSQL
postgres_pool: Optional[ThreadedConnectionPool] = None

async def initialize_db():
    """Initialize database connection pools on application startup."""
    global postgres_pool
    
    # Initialize PostgreSQL connection pool if configured
    if settings.POSTGRES_CONN_STR:
        try:
            postgres_pool = ThreadedConnectionPool(1, 10, settings.POSTGRES_CONN_STR)
            logger.info("PostgreSQL connection pool initialized")
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
    else:
        logger.warning("PostgreSQL connection string not provided, pool not initialized")

async def close_db_connections():
    """Close database connections on application shutdown."""
    global postgres_pool
    
    # Close PostgreSQL connection pool if initialized
    if postgres_pool:
        postgres_pool.closeall()
        logger.info("PostgreSQL connection pool closed")

@contextmanager
def get_mssql_connection():
    """Get a connection from the MS SQL Server."""
    if not settings.MSSQL_CONN_STR:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MS SQL Server connection not configured"
        )
    
    conn = None
    try:
        conn = pyodbc.connect(settings.MSSQL_CONN_STR)
        yield conn
    except pyodbc.Error as e:
        logger.error(f"MS SQL Server connection error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    finally:
        if conn:
            conn.close()

@contextmanager
def get_postgres_connection():
    """Get a connection from the PostgreSQL connection pool."""
    global postgres_pool
    
    if not postgres_pool:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PostgreSQL connection pool not initialized"
        )
    
    conn = None
    try:
        conn = postgres_pool.getconn()
        yield conn
    except (psycopg2.Error, AttributeError) as e:
        logger.error(f"PostgreSQL connection error: {e}")
        if conn and postgres_pool:
            postgres_pool.putconn(conn)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    finally:
        if conn and postgres_pool:
            postgres_pool.putconn(conn)

def is_safe_query(query: str) -> bool:
    """
    Basic SQL injection prevention by checking for unsafe SQL operations.
    
    Args:
        query: The SQL query to validate
        
    Returns:
        bool: True if the query appears safe, False otherwise
    """
    unsafe_patterns = [
        "DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "TRUNCATE ",
        "CREATE ", "GRANT ", "EXEC ", "EXECUTE ", "TRUNCATE ", "INTO OUTFILE",
        "LOAD DATA", "SCHEMA", "SHUTDOWN", "UNION ALL", "UNION SELECT"
    ]
    
    query_upper = query.upper()
    return not any(pattern in query_upper for pattern in unsafe_patterns)

def execute_parameterized_query(
    db: str, 
    query: str, 
    params: Optional[List[Any]] = None,
    page: int = 1,
    page_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute a parameterized SQL query on the specified database with pagination support.
    
    Args:
        db: Database to use ('mssql' or 'postgres')
        query: SQL query with parameter placeholders (? for MSSQL, %s for PostgreSQL)
        params: List of parameter values to be sanitized and inserted
        page: Page number for paginated results (starting from 1)
        page_size: Number of records per page, if None uses settings.MAX_RESULTS
        
    Returns:
        Dictionary containing:
            - data: List of dictionaries representing the query results
            - pagination: Dictionary with pagination metadata
            - count: Total number of records matching the query
            
    Raises:
        HTTPException: If a database error occurs
    """
    if params is None:
        params = []
    
    if page_size is None:
        page_size = settings.MAX_RESULTS
    
    if page < 1:
        page = 1
        
    # Safety check for query content
    if not is_safe_query(query):
        logger.warning(f"Unsafe SQL query attempted: {query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Operation not permitted in this query"
        )
    
    results = []
    total_count = 0
    
    try:
        # Convert query placeholders based on database type
        if db == "postgres" and "?" in query and params:
            # Convert ? placeholders to %s for PostgreSQL
            # Note: This is a simple replacement - for a real app, use a proper SQL parser
            pg_query = query.replace("?", "%s")
            logger.debug(f"Converted placeholders for PostgreSQL: {pg_query}")
            query = pg_query
        elif db == "mssql" and "%s" in query and params:
            # Convert %s placeholders to ? for MSSQL
            ms_query = query.replace("%s", "?")
            logger.debug(f"Converted placeholders for MSSQL: {ms_query}")
            query = ms_query
        
        # Calculate pagination 
        offset = (page - 1) * page_size
        
        # For non-DML statements, we need to get the total count and apply pagination
        is_select_query = query.strip().upper().startswith("SELECT")
        
        # Execute the query with parameters based on database type
        if db == "mssql":
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                
                if is_select_query:
                    # Execute count query to get total records
                    count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
                    cursor.execute(count_query, params)
                    total_count = cursor.fetchone()[0]
                    
                    # Add pagination to the original query if not already present
                    # This is SQL Server specific pagination (2012+)
                    if not re.search(r'OFFSET\s+\d+\s+ROWS', query, re.IGNORECASE):
                        paginated_query = f"{query} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                        cursor.execute(paginated_query, params)
                    else:
                        cursor.execute(query, params)
                else:
                    # For non-SELECT queries
                    cursor.execute(query, params)
                
                if cursor.description:  # Check if the query returns results
                    rows = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
                    
                    # For non-SELECT queries that return results, use actual count
                    if not is_select_query:
                        total_count = len(results)
                
                # For INSERT/UPDATE/DELETE that doesn't return rows but has an impact
                if not results and cursor.rowcount > 0:
                    results = [{"affected_rows": cursor.rowcount}]
                    total_count = cursor.rowcount
                
        elif db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    if is_select_query:
                        # Execute count query to get total records
                        count_query = f"SELECT COUNT(*) FROM ({query}) as count_query"
                        cursor.execute(count_query, params)
                        total_count = cursor.fetchone()[0]
                        
                        # Add pagination to the original query if not already present
                        if not re.search(r'LIMIT\s+\d+\s+OFFSET\s+\d+', query, re.IGNORECASE):
                            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
                            cursor.execute(paginated_query, params)
                        else:
                            cursor.execute(query, params)
                    else:
                        # For non-SELECT queries
                        cursor.execute(query, params)
                    
                    # Check if the query returns results
                    if cursor.description:  
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in rows]
                        
                        # For non-SELECT queries that return results, use actual count
                        if not is_select_query:
                            total_count = len(results)
                    
                    # For INSERT/UPDATE/DELETE that doesn't return rows but has an impact
                    elif cursor.rowcount > 0:
                        results = [{"affected_rows": cursor.rowcount}]
                        total_count = cursor.rowcount
                        
                # Commit changes if this is a modification operation
                if not is_select_query:
                    conn.commit()
                    logger.info(f"Changes committed to PostgreSQL database")
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_records": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1 if has_next else None,
            "prev_page": page - 1 if has_prev else None
        }
        
        return {
            "data": results,
            "pagination": pagination,
            "count": total_count
        }
        
    except Exception as e:
        logger.error(f"Database error during parameterized query execution: {str(e)}")
        # Log the full error for debugging but don't expose it to clients
        # Sanitize error message to avoid exposing sensitive info
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during query execution"
        )

def parse_for_parameters(query: str) -> Tuple[str, List[Any]]:
    """
    Parse a raw SQL query to extract potential parameters.
    This implementation handles common SQL literals including strings and numbers.
    
    Args:
        query: Raw SQL query with potential literal values
        
    Returns:
        Tuple containing:
            - Modified query with parameter placeholders
            - List of extracted parameter values
    """
    # This enhanced implementation handles both string and numeric parameters
    # while still avoiding table/column names and SQL keywords
    
    # First, remove SQL comments to avoid false positives
    cleaned_query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    cleaned_query = re.sub(r'/\*.*?\*/', '', cleaned_query, flags=re.DOTALL)
    
    # Store all parameters we find
    all_params = []
    modified_query = cleaned_query
    
    # Track positions to adjust offsets as we replace
    offset_adjustment = 0
    
    # 1. Extract and replace string literals (handle both single and double quotes)
    # Note: This doesn't handle escaped quotes within strings - a more robust parser would
    string_pattern = r"'([^']*)'|\"([^\"]*)\""
    
    string_matches = list(re.finditer(string_pattern, cleaned_query))
    
    for match in string_matches:
        # Get the matched string and its group (either group 1 or 2 will have the content)
        param_value = match.group(1) if match.group(1) is not None else match.group(2)
        all_params.append(param_value)
        
        # Calculate position in the modified query
        start_pos = match.start() - offset_adjustment
        end_pos = match.end() - offset_adjustment
        
        # Replace with placeholder in modified query
        old_length = end_pos - start_pos
        modified_query = modified_query[:start_pos] + "?" + modified_query[end_pos:]
        
        # Update offset adjustment
        offset_adjustment += old_length - 1  # -1 for the "?" we inserted
    
    # 2. Now extract numeric parameters as well (only in WHERE, HAVING clauses to avoid table aliases)
    # First, identify WHERE and HAVING clauses
    where_clause_matches = list(re.finditer(r'\bWHERE\b|\bHAVING\b|\bON\b', modified_query, re.IGNORECASE))
    
    if where_clause_matches:
        # Get the position of the first WHERE/HAVING/ON
        condition_start = where_clause_matches[0].start()
        condition_section = modified_query[condition_start:]
        
        # Look for numeric values in conditions (avoid capturing things like LIMIT 10)
        # Match numbers in comparison operations
        number_pattern = r'(=|>|<|>=|<=|!=|<>)\s*(-?\d+(?:\.\d+)?)\b(?!\s*\()'
        
        number_matches = list(re.finditer(number_pattern, condition_section))
        
        # Track a separate offset adjustment for the condition section
        condition_offset_adjustment = 0
        
        for match in number_matches:
            operator = match.group(1)
            number_value = match.group(2)
            
            # Try to convert to appropriate numeric type
            try:
                if '.' in number_value:
                    param_value = float(number_value)
                else:
                    param_value = int(number_value)
                
                all_params.append(param_value)
                
                # Calculate position in the modified condition section
                value_start = match.start(2) - condition_offset_adjustment
                value_end = match.end(2) - condition_offset_adjustment
                
                # Replace with placeholder in modified condition section
                value_length = value_end - value_start
                condition_section = (condition_section[:value_start] + 
                                    "?" + 
                                    condition_section[value_end:])
                
                # Update the condition offset adjustment
                condition_offset_adjustment += value_length - 1
            except ValueError:
                # Skip if we can't parse the number for any reason
                continue
        
        # Reconstruct the full query with the modified condition section
        modified_query = modified_query[:condition_start] + condition_section
    
    # If no parameters were extracted, return the original query
    if not all_params:
        return query, []
    
    logger.info(f"Parameterized query: {modified_query}")
    logger.info(f"Parameters extracted: {all_params}")
    
    return modified_query, all_params

def test_db_connections() -> Dict[str, bool]:
    """Test connections to configured databases."""
    status = {
        "mssql": False,
        "postgres": False
    }
    
    # Test MS SQL connection
    if settings.MSSQL_CONN_STR:
        try:
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                status["mssql"] = True
        except Exception as e:
            logger.error(f"MS SQL connection test failed: {e}")
    
    # Test PostgreSQL connection
    if postgres_pool:
        try:
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    status["postgres"] = True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
    
    return status
