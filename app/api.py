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
    is_safe_query, test_db_connections,
    execute_parameterized_query, parse_for_parameters
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
    Execute a SQL query against the specified database with pagination.
    
    Args:
        payload: Contains the database type, SQL query to execute, and optional
                pagination parameters (page, page_size)
        
    Returns:
        QueryResult: The results of the SQL query with pagination metadata
        
    Raises:
        HTTPException: If the query is unsafe or if a database error occurs
    """
    logger.info(f"Running SQL query on {payload.db} (page {payload.page}, size {payload.page_size})")
    
    # Validate query for safety
    if not is_safe_query(payload.query):
        logger.warning(f"Unsafe SQL query attempted: {payload.query}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Operation not permitted in this query"
        )
        
    try:
        # Parse and extract parameters from the raw query
        parameterized_query, params = parse_for_parameters(payload.query)
        
        # Execute the query with parameters and pagination
        # Ensure page is always an integer (default to 1 if None)
        page = payload.page if payload.page is not None else 1
        
        result = execute_parameterized_query(
            db=payload.db, 
            query=parameterized_query, 
            params=params,
            page=page,
            page_size=payload.page_size
        )
        
        # Return the result with pagination metadata
        return {
            "status": "success", 
            "data": result["data"],
            "count": result["count"],
            "pagination": result["pagination"]
        }
        
    except Exception as e:
        logger.error(f"Database error during query execution: {str(e)}")
        # Don't expose detailed error messages to the client 
        # as they might contain sensitive information
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred. Please check your query syntax or contact the administrator."
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
            detail="Error processing natural language query. Please try a different phrasing."
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
        result = None  # Initialize the result variable
        
        if db == "mssql":
            query = """
                SELECT 
                    TABLE_NAME, 
                    COLUMN_NAME, 
                    DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS
            """
            # Using a large page_size to retrieve all records
            result = execute_parameterized_query(db, query, page=1, page_size=1000)
                
        elif db == "postgres":
            query = """
                SELECT 
                    table_name, 
                    column_name, 
                    data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
            """
            # Using a large page_size to retrieve all records
            result = execute_parameterized_query(db, query, page=1, page_size=1000)
        
        if result:  # Check if result exists before accessing it
            return {
                "status": "success", 
                "db_schema": result["data"],
                "count": result["count"],
                "pagination": result["pagination"]
            }
        else:
            # If no result, return an empty schema with pagination
            empty_pagination = {
                "page": 1,
                "page_size": 0,
                "total_records": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
                "next_page": None,
                "prev_page": None
            }
            return {
                "status": "error", 
                "db_schema": [],
                "count": 0,
                "pagination": empty_pagination
            }
        
    except Exception as e:
        logger.error(f"Error discovering schema: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the database schema. Please ensure the database is properly configured."
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
            # Get list of tables
            if prefix:
                query = """
                    SELECT DISTINCT TABLE_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME LIKE ?
                    ORDER BY TABLE_NAME
                """
                # Using a large page_size to retrieve all records
                tables_result = execute_parameterized_query(db, query, [f"{prefix}%"], page=1, page_size=1000)
            else:
                query = """
                    SELECT DISTINCT TABLE_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    ORDER BY TABLE_NAME
                """
                # Using a large page_size to retrieve all records
                tables_result = execute_parameterized_query(db, query, page=1, page_size=1000)
            
            tables = [row["TABLE_NAME"] for row in tables_result["data"]]
            
            # Get column info for each table
            for table in tables:
                query = """
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """
                # Using a large page_size to retrieve all records
                columns_result = execute_parameterized_query(db, query, [table], page=1, page_size=1000)
                
                columns = [f"{row['COLUMN_NAME']} ({row['DATA_TYPE']})" for row in columns_result["data"]]
                table_summaries.append(f"{table}: {', '.join(columns)}")
            
        elif db == "postgres":
            # Get list of tables
            if prefix:
                query = """
                    SELECT DISTINCT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name LIKE %s
                    ORDER BY table_name
                """
                # Using a large page_size to retrieve all records
                tables_result = execute_parameterized_query(db, query, [f"{prefix}%"], page=1, page_size=1000)
            else:
                query = """
                    SELECT DISTINCT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                # Using a large page_size to retrieve all records
                tables_result = execute_parameterized_query(db, query, page=1, page_size=1000)
            
            tables = [row["table_name"] for row in tables_result["data"]]
            
            # Get column info for each table
            for table in tables:
                query = """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """
                # Using a large page_size to retrieve all records
                columns_result = execute_parameterized_query(db, query, [table], page=1, page_size=1000)
                
                columns = [f"{row['column_name']} ({row['data_type']})" for row in columns_result["data"]]
                table_summaries.append(f"{table}: {', '.join(columns)}")
        
        # Add pagination metadata for consistency
        total_count = len(table_summaries)
        
        # Create pagination metadata
        pagination = {
            "page": 1,
            "page_size": total_count,
            "total_records": total_count,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
            "next_page": None,
            "prev_page": None
        }
        
        return {
            "status": "success", 
            "summary": table_summaries,
            "count": total_count,
            "pagination": pagination
        }
        
    except Exception as e:
        logger.error(f"Error getting schema summary: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the database schema summary. Please check your connection and try again."
        )
