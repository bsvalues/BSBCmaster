import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from .security import get_api_key
from .models import (
    SQLQuery, NLPrompt, QueryResult, SQLTranslation, 
    SchemaResponse, SchemaSummary, HealthResponse
)
from .db import (
    get_mssql_connection, get_postgres_connection, 
    is_safe_query, test_db_connections
)
from .settings import settings

logger = logging.getLogger("mcp_assessor_api")
router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the index page with API documentation."""
    from datetime import datetime
    # Get base URL for API endpoints
    base_url = str(request.base_url).rstrip('/')
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": settings.APP_NAME,
        "version": "1.0.0",
        "description": "API service for accessing and querying assessment data",
        "base_url": base_url,
        "current_year": datetime.now().year
    })

@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of the API and its database connections.
    
    Returns:
        HealthResponse: The health status of the API and its database connections
    """
    db_status = test_db_connections()
    
    return {
        "status": "ok", 
        "db_connections": db_status
    }

@router.post(
    "/api/run-query", 
    response_model=QueryResult,
    dependencies=[Depends(get_api_key)]
)
async def run_sql_query(payload: SQLQuery):
    """
    Execute a SQL query against the specified database.
    
    Args:
        payload: The SQL query to execute with the target database
        
    Returns:
        QueryResult: The results of the SQL query
        
    Raises:
        HTTPException: If the query is unsafe or if a database error occurs
    """
    logger.info(f"Running SQL query on {payload.db}")
    
    # Validate query for safety
    if not is_safe_query(payload.query):
        logger.warning(f"Unsafe SQL query attempted: {payload.query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Operation not permitted in this query"
        )
        
    try:
        results = []
        if payload.db == "mssql":
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(payload.query)
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                
        elif payload.db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(payload.query)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
                    
        # Apply result limitation
        total_count = len(results)
        truncated = total_count > settings.MAX_RESULTS
        limited_results = results[:settings.MAX_RESULTS]
        
        return {
            "status": "success", 
            "data": limited_results,
            "count": total_count,
            "truncated": truncated
        }
        
    except Exception as e:
        logger.error(f"Database error during query execution: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post(
    "/api/nl-to-sql", 
    response_model=SQLTranslation,
    dependencies=[Depends(get_api_key)]
)
async def nl_to_sql(prompt: NLPrompt):
    """
    Convert natural language prompt to SQL query.
    
    Args:
        prompt: The natural language prompt to convert to SQL
        
    Returns:
        SQLTranslation: The translated SQL query
        
    Raises:
        HTTPException: If an error occurs during translation
    """
    logger.info(f"Processing NL->SQL request: {prompt.prompt}")
    
    try:
        # This would normally call an LLM service
        # Simulated response for demonstration
        if prompt.db == "postgres":
            # Example implementation - in a real system, this would call an LLM
            if "parcel" in prompt.prompt.lower() and "value" in prompt.prompt.lower():
                simulated_sql = "SELECT * FROM parcels WHERE total_value > 500000 LIMIT 100"
            else:
                simulated_sql = f"SELECT * FROM properties LIMIT 50"
        else:
            simulated_sql = f"SELECT TOP 50 * FROM properties"
        
        return {
            "status": "success", 
            "sql": simulated_sql
        }
        
    except Exception as e:
        logger.error(f"Error in NL->SQL processing: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing natural language query"
        )

@router.get(
    "/api/discover-schema", 
    response_model=SchemaResponse,
    dependencies=[Depends(get_api_key)]
)
async def discover_schema(db: str = Query(..., regex="^(mssql|postgres)$")):
    """
    Discover and return the database schema.
    
    Args:
        db: The database to discover the schema for (mssql or postgres)
        
    Returns:
        SchemaResponse: The database schema
        
    Raises:
        HTTPException: If a database error occurs
    """
    logger.info(f"Discovering schema for {db}")
    
    try:
        if db == "mssql":
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        TABLE_NAME, 
                        COLUMN_NAME, 
                        DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS
                """)
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                
        elif db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            table_name, 
                            column_name, 
                            data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public'
                    """)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
        
        return {"status": "success", "db_schema": results}
        
    except Exception as e:
        logger.error(f"Error discovering schema: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving database schema"
        )

@router.get(
    "/api/schema-summary", 
    response_model=SchemaSummary,
    dependencies=[Depends(get_api_key)]
)
async def get_schema_summary(
    db: str = Query(..., regex="^(mssql|postgres)$"),
    prefix: str = Query("", max_length=50)
):
    """
    Get a summarized view of the database schema.
    
    Args:
        db: The database to get the schema summary for (mssql or postgres)
        prefix: Optional table name prefix to filter by
        
    Returns:
        SchemaSummary: A summary of the database schema
        
    Raises:
        HTTPException: If a database error occurs
    """
    logger.info(f"Getting schema summary for {db} with prefix '{prefix}'")
    
    try:
        table_summaries = []
        
        if db == "mssql":
            with get_mssql_connection() as conn:
                cursor = conn.cursor()
                
                # Get list of tables
                if prefix:
                    cursor.execute("""
                        SELECT DISTINCT TABLE_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME LIKE ?
                        ORDER BY TABLE_NAME
                    """, (f"{prefix}%",))
                else:
                    cursor.execute("""
                        SELECT DISTINCT TABLE_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        ORDER BY TABLE_NAME
                    """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get column info for each table
                for table in tables:
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME = ?
                        ORDER BY ORDINAL_POSITION
                    """, (table,))
                    
                    columns = [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]
                    table_summaries.append(f"{table}: {', '.join(columns)}")
                
        elif db == "postgres":
            with get_postgres_connection() as conn:
                with conn.cursor() as cursor:
                    
                    # Get list of tables
                    if prefix:
                        cursor.execute("""
                            SELECT DISTINCT table_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name LIKE %s
                            ORDER BY table_name
                        """, (f"{prefix}%",))
                    else:
                        cursor.execute("""
                            SELECT DISTINCT table_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                            ORDER BY table_name
                        """)
                    
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get column info for each table
                    for table in tables:
                        cursor.execute("""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        
                        columns = [f"{row[0]} ({row[1]})" for row in cursor.fetchall()]
                        table_summaries.append(f"{table}: {', '.join(columns)}")
        
        return {"status": "success", "summary": table_summaries}
        
    except Exception as e:
        logger.error(f"Error getting schema summary: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving database schema summary"
        )
