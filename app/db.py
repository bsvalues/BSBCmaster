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
    params: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Execute a parameterized SQL query on the specified database.
    
    Args:
        db: Database to use ('mssql' or 'postgres')
        query: SQL query with parameter placeholders (? for MSSQL, %s for PostgreSQL)
        params: List of parameter values to be sanitized and inserted
        
    Returns:
        List of dictionaries representing the query results
        
    Raises:
        HTTPException: If a database error occurs
    """
    if params is None:
        params = []
    
    if not is_safe_query(query):
        logger.warning(f"Unsafe SQL query attempted: {query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Operation not permitted in this query"
        )
    
    results = []
    
    try:
        if db == "mssql":
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if cursor.description:  # Check if the query returns results
                    rows = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
                
        elif db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if cursor.description:  # Check if the query returns results
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        results = [dict(zip(columns, row)) for row in rows]
        
        return results
        
    except Exception as e:
        logger.error(f"Database error during parameterized query execution: {str(e)}")
        # Sanitize error message to avoid exposing sensitive info
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during query execution"
        )

def parse_for_parameters(query: str) -> Tuple[str, List[Any]]:
    """
    Parse a raw SQL query to extract potential parameters.
    This is a basic implementation that handles common SQL literals.
    
    Args:
        query: Raw SQL query with potential literal values
        
    Returns:
        Tuple containing:
            - Modified query with parameter placeholders
            - List of extracted parameter values
    """
    # This implementation handles common SQL injection patterns, but 
    # in a production environment, consider using a proper SQL parser library
    
    # This regex will match:
    # 1. Strings in single quotes
    # 2. Numbers (integer and decimal)
    # But will avoid:
    # - Table names and column names
    # - SQL keywords and functions
    # - Comments
    
    # Static patterns to ignore (common SQL keywords that might appear in WHERE clauses)
    skip_patterns = [
        r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'GROUP\s+BY', r'ORDER\s+BY',
        r'HAVING\s+', r'JOIN\s+', r'LIMIT\s+', r'OFFSET\s+', r'AS\s+',
        r'AND\s+', r'OR\s+', r'NOT\s+', r'IS\s+NULL', r'IS\s+NOT\s+NULL',
        r'IN\s+\(', r'BETWEEN\s+', r'LIKE\s+', r'ILIKE\s+',
        r'COUNT\s*\(', r'SUM\s*\(', r'AVG\s*\(', r'MIN\s*\(', r'MAX\s*\(',
        r'DISTINCT\s+', r'UNION\s+', r'INTERSECT\s+', r'EXCEPT\s+'
    ]
    
    # Create a temp copy to avoid modifying the original too soon
    processed_query = query
    
    # Remove comments
    processed_query = re.sub(r'--.*?$', '', processed_query, flags=re.MULTILINE)
    processed_query = re.sub(r'/\*.*?\*/', '', processed_query, flags=re.DOTALL)
    
    # Skip obvious SQL keywords
    for pattern in skip_patterns:
        processed_query = re.sub(pattern, ' SKIP ', processed_query, flags=re.IGNORECASE)
    
    # Extract string literals (single-quoted)
    string_params = []
    string_pattern = r"'([^']*)'"
    
    for match in re.finditer(string_pattern, processed_query):
        string_params.append(match.group(1))
    
    # Replace quoted strings with placeholders
    modified_query = re.sub(string_pattern, '?', query) if string_params else query
    
    # For simplicity, we're only handling string parameters in this implementation
    # In a real implementation, you'd also handle numeric parameters and other types
    
    # Check if we actually made any changes
    if modified_query == query and not string_params:
        # No changes made, just return original
        return query, []
    
    logger.info(f"Parameterized query: {modified_query}")
    logger.info(f"Parameters extracted: {string_params}")
    
    return modified_query, string_params

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
