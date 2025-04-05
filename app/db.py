"""
This module handles database connections and SQL query execution.
"""

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

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
flask_db = None

def get_flask_db():
    """Get the Flask SQLAlchemy instance to ensure consistency."""
    global flask_db
    if flask_db is None:
        try:
            # Import the db from app_setup to ensure we use the same instance
            from app_setup import db as app_setup_db
            flask_db = app_setup_db
            logger.info("Using Flask SQLAlchemy instance from app_setup")
        except ImportError:
            logger.warning("Could not import db from app_setup, will use direct database connection")
    return flask_db

async def initialize_db():
    """Initialize database connection pools on application startup."""
    global pg_pool
    try:
        # First, try to get the Flask DB instance for model operations
        flask_db = get_flask_db()
        
        # Initialize PostgreSQL connection pool for raw queries
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.warning("No DATABASE_URL environment variable found")
            db_url = os.environ.get("DB_POSTGRES_URL")
        
        if db_url:
            logger.info("Using database URL for PostgreSQL connection")
            import psycopg2.pool
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, db_url
            )
            logger.info("PostgreSQL connection pool initialized successfully")
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

async def get_db_pool(db_type):
    """
    Get the appropriate database connection pool.
    
    Args:
        db_type: The database type (postgres, mssql)
        
    Returns:
        Database connection pool or None if unavailable
    """
    global pg_pool
    
    # Initialize the pool if needed
    if not pg_pool:
        try:
            await initialize_db()
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            return None
    
    # Return the appropriate pool based on database type
    if db_type == "postgres" or getattr(db_type, "value", "") == "postgres":
        return pg_pool
    else:
        logger.warning(f"Unsupported database type: {db_type}")
        return None

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
        
def get_pg_connection():
    """
    Alias for get_postgres_connection for consistency with query_executor module.
    """
    return get_postgres_connection()
    
def close_pg_connection(conn):
    """
    Return a PostgreSQL connection to the connection pool.
    
    Args:
        conn: The PostgreSQL connection to return to the pool
    """
    global pg_pool
    if conn and pg_pool:
        try:
            pg_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning PostgreSQL connection to pool: {str(e)}")

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
    # Get MAX_RESULTS from settings or use default
    max_results = 100  # Default value
    try:
        from app.settings import settings
        if hasattr(settings, 'MAX_RESULTS'):
            max_results = settings.MAX_RESULTS
    except (ImportError, AttributeError):
        logger.warning("Could not get MAX_RESULTS from settings, using default of 100")
    
    # Set default page size if not provided
    if page_size is None:
        page_size = max_results
    
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1 or page_size > max_results:
        page_size = max_results
    
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

def execute_query_with_explicit_params(
    db: str,
    query: str,
    params: Any,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    """
    Execute a query with explicit parameter handling, particularly useful for 
    PostgreSQL with various parameter styles.
    
    This function uses direct mogrification to safely substitute parameter values,
    which is especially useful for PostgreSQL when dealing with ? placeholders or
    :named parameters that need to be converted to PostgreSQL's %s style.
    
    Args:
        db: Database type (postgres, mssql)
        query: SQL query with ? or :name placeholders
        params: List or Dict of parameter values
        page: Page number for pagination (starting from 1)
        page_size: Number of results per page
        
    Returns:
        Dict containing query results and metadata
    """
    import time
    start_time = time.time()
    
    if db.lower() != "postgres":
        raise ValueError("This function is only for PostgreSQL queries")
    
    # Handle different parameter styles
    postgres_query = query
    postgres_params = params
    
    # Convert parameters based on their type
    if isinstance(params, dict):
        # For named parameters, convert :name to %s and build a parameter list
        named_params = []
        import re
        
        # Find all parameter names in the query
        param_names = re.findall(r':([a-zA-Z0-9_]+)', query)
        
        # Build the parameter list in order of appearance
        for name in param_names:
            if name in params:
                named_params.append(params[name])
            else:
                raise ValueError(f"Named parameter '{name}' not found in params dictionary")
        
        # Replace :name with %s placeholders
        postgres_query = re.sub(r':([a-zA-Z0-9_]+)', '%s', query)
        postgres_params = named_params
        
        logger.info(f"Converted named parameters query: {postgres_query}")
        logger.info(f"Parameter list: {postgres_params}")
    else:
        # For positional parameters (qmark style), just replace ? with %s
        postgres_query = query.replace('?', '%s')
        logger.info(f"Converted query placeholders: {postgres_query}")
    
    # For PostgreSQL, use direct safe SQL execution with mogrify
    conn = None
    try:
        # Get connection from pool
        conn = get_postgres_connection()
        
        # Create cursor
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Set a timeout for long-running queries
            cursor.execute("SET statement_timeout TO 30000")  # 30 seconds
            
            # First prepare the main query with pagination
            offset = (page - 1) * page_size
            paginated_query = f"{postgres_query} LIMIT {page_size} OFFSET {offset}"
            
            try:
                # Log the mogrified query (with parameters substituted) for debugging
                if postgres_params:
                    debug_query = cursor.mogrify(paginated_query, postgres_params).decode('utf-8')
                    logger.info(f"Executing: {debug_query}")
            except Exception as e:
                logger.warning(f"Could not create debug query: {str(e)}")
            
            # Execute the paginated query safely with parameters
            cursor.execute(paginated_query, postgres_params)
            results = cursor.fetchall()
            
            # Now get total count with a separate query
            # We use tuple params to ensure parameters are properly passed to the subquery
            count_query = f"SELECT COUNT(*) AS total FROM ({postgres_query}) AS count_subquery"
            
            try:
                if postgres_params:
                    debug_count = cursor.mogrify(count_query, postgres_params).decode('utf-8')
                    logger.info(f"Count query: {debug_count}")
            except Exception as e:
                logger.warning(f"Could not create debug count query: {str(e)}")
            
            # Execute the count query safely
            cursor.execute(count_query, postgres_params)
            count_result = cursor.fetchone()
            total_count = count_result["total"] if count_result else 0
            
            # Create pagination metadata
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
            has_next = page < total_pages
            has_prev = page > 1
            
            pagination = {
                "page": page,
                "pages": total_pages,
                "page_size": page_size,
                "total": total_count,
                "has_next": has_next,
                "has_prev": has_prev,
            }
            
            # Get column types
            column_types = {}
            if results:
                for key in results[0].keys():
                    column_types[key] = str(type(results[0][key]).__name__)
            
            # Format results as list of dictionaries
            formatted_results = [dict(row) for row in results]
            
            # Execution time
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Build final result
            return {
                "status": "success",
                "data": formatted_results,
                "execution_time": execution_time,
                "pagination": pagination,
                "column_types": column_types
            }
    except Exception as e:
        logger.error(f"Error in execute_query_with_explicit_params: {str(e)}")
        raise
    finally:
        # Return connection to pool
        if conn and pg_pool:
            pg_pool.putconn(conn)

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
            # Set query timeout (default to 30 seconds if not in settings)
            timeout_seconds = 30  # Default timeout
            try:
                from app.settings import settings
                if hasattr(settings, 'TIMEOUT_SECONDS'):
                    timeout_seconds = settings.TIMEOUT_SECONDS
            except (ImportError, AttributeError):
                logger.warning("Could not get TIMEOUT_SECONDS from settings, using default of 30 seconds")
                
            cursor.execute(f"SET statement_timeout TO {timeout_seconds * 1000}")
            
            try:
                # Check if the query is expected to return results (not a schema query)
                if "information_schema.columns" in query or "information_schema.tables" in query:
                    # For schema queries, skip the count and just execute the main query
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    # No pagination for schema queries
                    pagination = {
                        "page": 1,
                        "pages": 1,
                        "page_size": len(results),
                        "total": len(results),
                        "has_next": False,
                        "has_prev": False,
                    }
                else:
                    # Regular query with pagination
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
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                # Print more detailed error information for debugging
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
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