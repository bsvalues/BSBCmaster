"""
This module handles database connections and SQL query execution.
"""

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection pools
pg_pool = None

async def initialize_db():
    """Initialize database connection pools on application startup."""
    global pg_pool
    try:
        # Initialize PostgreSQL connection pool
        if settings.DB_POSTGRES_URL:
            import psycopg2.pool
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, settings.DB_POSTGRES_URL
            )
            logger.info("PostgreSQL connection pool initialized")
        else:
            logger.warning("PostgreSQL connection URL not provided")
            # Log the environment variable
            db_url = os.environ.get("DATABASE_URL")
            if db_url:
                logger.info("Found DATABASE_URL environment variable, using it for PostgreSQL connection")
                import psycopg2.pool
                pg_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 10, db_url
                )
                logger.info("PostgreSQL connection pool initialized with DATABASE_URL")
                
                # Set the DB_POSTGRES_URL in settings as well for consistency
                from app.settings import settings
                settings.DB_POSTGRES_URL = db_url
            else:
                logger.warning("No PostgreSQL connection URL available")
    except Exception as e:
        logger.error(f"Error initializing database connections: {str(e)}")
        # Don't raise the exception, just log it
        logger.error("Continuing without database connection")

async def close_db_connections():
    """Close database connections on application shutdown."""
    global pg_pool
    if pg_pool:
        pg_pool.closeall()
        logger.info("PostgreSQL connection pool closed")

def get_postgres_connection():
    """Get a connection from the PostgreSQL connection pool."""
    global pg_pool
    if not pg_pool:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection not initialized",
        )
    
    try:
        conn = pg_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Error getting PostgreSQL connection: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}",
        )

def is_safe_query(query: str) -> bool:
    """
    Basic SQL injection prevention by checking for unsafe SQL operations.
    
    Args:
        query: The SQL query to validate
        
    Returns:
        bool: True if the query appears safe, False otherwise
    """
    # Normalize the query - lowercase, remove extra whitespace
    normalized_query = ' '.join(query.lower().split())
    
    # Check for potentially harmful SQL operations
    unsafe_patterns = [
        r'\bdrop\s+(?:table|database|schema|view|index|user)\b',
        r'\btruncate\s+(?:table)\b',
        r'\bdelete\s+(?:from\b|[^;]+;)',  # Only block full DELETE operations
        r'\balter\s+(?:table|database|schema|system)\b',
        r'\bcreate\s+(?:table|database|schema|view|user)\b',
        r'\binsert\s+into\b',
        r'\bupdate\s+(?:[^;]+set)\b',
        r'\bgrant\b',
        r'\brevoke\b',
        r'\bcopy\b',
        r'(?:--|#|\/\*).*',  # SQL comments that might hide code
        r';\s*(?:\w+)',      # Multiple statements
        r'(?:exec|execute|call|xp_cmdshell)',  # Execute commands
        r'(?:union\s+(?:all\s+)?select)',  # UNION-based injection
        r'(?:into\s+(?:outfile|dumpfile))',  # File operations
        r'(?:load_file|benchmark|sleep)',  # Functions used in injection
    ]
    
    # Check for unsafe patterns
    for pattern in unsafe_patterns:
        if re.search(pattern, normalized_query):
            return False
    
    # If no unsafe patterns were found, consider it safe
    return True

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
    # Set default page size from settings if not provided
    if page_size is None:
        page_size = settings.MAX_RESULTS
    
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1 or page_size > settings.MAX_RESULTS:
        page_size = settings.MAX_RESULTS
    
    # Safety check
    if not is_safe_query(query):
        logger.warning(f"Unsafe query detected: {query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Query contains potentially unsafe operations and was rejected.",
        )
    
    # Start timing for performance measurement
    start_time = time.time()
    
    # If params is None, use empty list for consistency
    if params is None:
        params = []
    
    # Execute query based on database type
    if db.lower() == 'postgres':
        try:
            result = execute_postgres_query(query, params, page, page_size, start_time)
            return result
        except Exception as e:
            logger.error(f"PostgreSQL query error: {str(e)}, Query: {query}, Params: {params}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unsupported database type: {db}",
        )

def execute_postgres_query(
    query: str, 
    params: Optional[List[Any]], 
    page: int, 
    page_size: int,
    start_time: float
) -> Dict[str, Any]:
    """Execute a query on PostgreSQL with pagination."""
    conn = None
    try:
        # Get connection from pool
        conn = get_postgres_connection()
        
        # Create cursor with dictionary results
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Set query timeout
            cursor.execute(f"SET statement_timeout TO {settings.TIMEOUT_SECONDS * 1000}")
            
            # Execute count query first (for pagination metadata)
            count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS subquery"
            cursor.execute(count_query, params)
            count_result = cursor.fetchone()
            total_count = count_result["total"] if count_result else 0
            
            # Calculate pagination
            offset = (page - 1) * page_size
            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
            
            # Execute main query with pagination
            cursor.execute(paginated_query, params)
            results = cursor.fetchall()
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
            has_next = page < total_pages
            has_prev = page > 1
            
            # Create pagination info
            pagination = {
                "page": page,
                "pages": total_pages,
                "page_size": page_size,
                "total": total_count,
                "has_next": has_next,
                "has_prev": has_prev,
            }
            
            # Format results as list of dictionaries
            formatted_results = [dict(row) for row in results]
            
            # Calculate query execution time
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "data": formatted_results,
                "execution_time": execution_time,
                "pagination": pagination
            }
    finally:
        # Return connection to pool
        if conn and pg_pool:
            pg_pool.putconn(conn)

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
    # Initialize parameters list
    params = []
    
    # First, handle string literals (quoted values)
    def replace_string_literals(match):
        # Extract the string content (without quotes)
        string_content = match.group(1)
        params.append(string_content)
        return "%s"  # PostgreSQL parameter placeholder
    
    # Handle single-quoted strings
    query = re.sub(r"'([^']*)'", replace_string_literals, query)
    
    # Handle numeric literals
    def replace_numeric_literals(match):
        # Extract the numeric value
        numeric_value = match.group(1)
        # Convert to appropriate numeric type
        if '.' in numeric_value:
            value = float(numeric_value)
        else:
            value = int(numeric_value)
        params.append(value)
        return "%s"  # PostgreSQL parameter placeholder
    
    # Replace numeric literals, but skip parameter placeholders
    query = re.sub(r'(?<![%\w])([-+]?\d+(\.\d+)?)', replace_numeric_literals, query)
    
    return query, params

def test_db_connections() -> Dict[str, bool]:
    """Test connections to configured databases."""
    results = {
        "postgres": False,
        "mssql": False
    }
    
    # Test PostgreSQL connection
    if pg_pool:
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            if pg_pool:
                pg_pool.putconn(conn)
            results["postgres"] = True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {str(e)}")
    else:
        logger.warning("PostgreSQL connection pool not initialized")
    
    # MSSQL connection would be tested here if implemented
    
    return results