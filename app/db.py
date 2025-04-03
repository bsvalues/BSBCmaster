import logging
import pyodbc
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from typing import Optional, Dict, Any
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
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
