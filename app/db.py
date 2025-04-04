"""
This module handles database connections and SQL query execution.
"""

import time
import re
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.settings import Settings

settings = Settings()

# Create connection pools
postgres_pool = None
mssql_pool = None


async def initialize_db():
    """Initialize database connection pools on application startup."""
    global postgres_pool
    
    # Initialize PostgreSQL connection pool if settings are provided
    if settings.POSTGRES_CONN_STR:
        try:
            postgres_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=settings.POSTGRES_CONN_STR
            )
            print(f"PostgreSQL connection pool initialized successfully")
        except Exception as e:
            print(f"Error initializing PostgreSQL connection pool: {e}")
            postgres_pool = None
    else:
        print("PostgreSQL connection string not provided, skipping initialization")


async def close_db_connections():
    """Close database connections on application shutdown."""
    global postgres_pool
    
    # Close PostgreSQL connection pool
    if postgres_pool:
        postgres_pool.closeall()
        print("PostgreSQL connection pool closed")


def get_postgres_connection():
    """Get a connection from the PostgreSQL connection pool."""
    global postgres_pool
    
    if not postgres_pool:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PostgreSQL database not configured"
        )
    
    conn = postgres_pool.getconn()
    if not conn:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get PostgreSQL connection from pool"
        )
    
    return conn


def is_safe_query(query: str) -> bool:
    """
    Basic SQL injection prevention by checking for unsafe SQL operations.
    
    Args:
        query: The SQL query to validate
        
    Returns:
        bool: True if the query appears safe, False otherwise
    """
    # Remove comments to prevent comment-based SQL injection
    query = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)
    query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)
    
    # Normalize whitespace
    query = " ".join(query.split()).strip().lower()
    
    # Check for potentially harmful operations
    unsafe_patterns = [
        # Data modification
        r"\s*drop\s+", 
        r"\s*truncate\s+",
        r"\s*alter\s+",
        r"\s*create\s+",
        r"\s*rename\s+",
        
        # Database modification
        r"\s*grant\s+",
        r"\s*revoke\s+",
        
        # Execution
        r"\s*execute\s+",
        r"\s*exec\s+",
        
        # System commands
        r"xp_cmdshell",
        r"sp_execute_external_script",
        
        # Multiple statements
        r";\s*\w+",  # Catch multiple statements (e.g., "SELECT 1; DROP TABLE")
    ]
    
    for pattern in unsafe_patterns:
        if re.search(pattern, query):
            return False
    
    # Check for balanced quotes to detect quote escaping attempts
    single_quotes = query.count("'")
    double_quotes = query.count('"')
    
    if single_quotes % 2 != 0 or double_quotes % 2 != 0:
        return False
    
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
    if not is_safe_query(query):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Potentially unsafe query detected. Please review your query and try again."
        )
    
    # Set default page size if not provided
    if page_size is None:
        page_size = settings.MAX_RESULTS
    
    # Ensure valid pagination parameters
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = settings.MAX_RESULTS
    
    # Track execution time
    start_time = time.time()
    
    if db.lower() == 'postgres':
        return execute_postgres_query(query, params, page, page_size, start_time)
    else:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unsupported database type: {db}"
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
    cursor = None
    try:
        conn = get_postgres_connection()
        
        # First get the total count of rows for pagination
        # This approach is not perfect but provides a reasonable estimate
        cursor = conn.cursor()
        
        # Use a subquery to get an accurate count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        cursor.execute(count_query, params)
        total_items = cursor.fetchone()[0]
        
        # Close the count cursor and create a new one for the main query
        cursor.close()
        
        # Add pagination to the query
        offset = (page - 1) * page_size
        paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
        
        # Execute the paginated query with dictionary cursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(paginated_query, params)
        
        # Get column names
        column_names = [desc[0] for desc in cursor.description]
        
        # Fetch the results
        results = cursor.fetchall()
        
        # Calculate total pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Calculate has_next and has_prev
        has_next = page < total_pages
        has_prev = page > 1
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Create pagination metadata
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
        
        return {
            "data": [dict(row) for row in results],  
            "pagination": pagination,
            "columns": column_names,
            "query": query,
            "execution_time": execution_time
        }
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            postgres_pool.putconn(conn)


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
    params = []
    
    # Function to replace string literals with placeholders
    def replace_string_literals(match):
        # Extract the string content without quotes
        value = match.group(1)
        params.append(value)
        return "%s"  # PostgreSQL placeholders
    
    # Function to replace numeric literals with placeholders
    def replace_numeric_literals(match):
        value = match.group(0)
        # Handle floating point or integer
        if '.' in value:
            params.append(float(value))
        else:
            params.append(int(value))
        return "%s"  # PostgreSQL placeholders
    
    # Replace string literals (handles both single and double quotes)
    pattern_single_quote = r"'((?:[^'\\]|\\.)*?)'(?!')(?!\w)"  # Handles escaped quotes
    pattern_double_quote = r'"((?:[^"\\]|\\.)*?)"(?!")(?!\w)'  # Handles escaped quotes
    
    # Apply string replacements
    query = re.sub(pattern_single_quote, replace_string_literals, query)
    query = re.sub(pattern_double_quote, replace_string_literals, query)
    
    # Replace numeric literals, avoiding table/column names
    # This pattern matches numbers that are not part of identifiers
    numeric_pattern = r'(?<!\w)(\d+\.\d+|\d+)(?!\w|\.\w)'
    query = re.sub(numeric_pattern, replace_numeric_literals, query)
    
    return query, params


def test_db_connections() -> Dict[str, bool]:
    """Test connections to configured databases."""
    status = {"postgres": False}
    
    # Test PostgreSQL connection
    if settings.POSTGRES_CONN_STR:
        try:
            conn = None
            if postgres_pool:
                conn = postgres_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                status["postgres"] = True
        except Exception as e:
            print(f"PostgreSQL connection test failed: {e}")
        finally:
            if conn:
                postgres_pool.putconn(conn)
    
    return status