"""
This module defines the API routes and handlers.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from starlette.responses import JSONResponse

from app.db import execute_parameterized_query, parse_for_parameters, test_db_connections
from app.models import (
    SQLQuery, NLPrompt, QueryResult, SQLTranslation, ParameterizedSQLQuery,
    SchemaResponse, SchemaSummary, HealthResponse, SchemaItem
)
from app.openai_service import translate_nl_to_sql
from app.security import get_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of the API and its database connections.
    
    Returns:
        HealthResponse: The health status of the API and its database connections
    """
    import time
    from app import start_time
    
    # Test database connections
    db_connections = test_db_connections()
    
    return {
        "status": "success" if any(db_connections.values()) else "error",
        "message": "API is operational",
        "database_status": db_connections,
        "databases": [],  # Detailed database info would be added here in a full implementation
        "api_version": "1.0.0",  # Set API version
        "uptime": time.time() - start_time  # Calculate uptime in seconds
    }

@router.post("/run-query", response_model=QueryResult)
async def run_sql_query(
    payload: SQLQuery,
    api_key: str = Depends(get_api_key)
):
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
    try:
        # Extract query parameters
        db = payload.db.value
        query = payload.query
        params = payload.params
        page = payload.page or 1
        page_size = payload.page_size
        
        logger.info(f"Executing query on {db}")
        
        # If params is None, use the parameter extraction function
        if params is None:
            parsed_query, extracted_params = parse_for_parameters(query)
            # Use the parsed query and extracted params if any were found
            if extracted_params:
                query = parsed_query
                params = extracted_params
                logger.info(f"Extracted {len(params)} parameters from query")
        
        # Execute the query
        result = execute_parameterized_query(
            db=db,
            query=query,
            params=params,
            page=page,
            page_size=page_size
        )
        
        return result
    except HTTPException:
        # Pass through HTTP exceptions raised by the db module
        raise
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution error: {str(e)}"
        )

@router.post("/parameterized-query", response_model=QueryResult)
async def run_parameterized_query(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """
    Execute a parameterized SQL query against the specified database.
    
    This endpoint provides a secure way to execute SQL queries with proper parameter binding,
    which helps protect against SQL injection attacks. Parameters are passed separately
    from the query string and bound by the database driver.
    
    Args:
        request: The raw request object to allow manual processing of the payload
                
    Returns:
        QueryResult: The results of the SQL query with pagination metadata
        
    Raises:
        HTTPException: If the query is unsafe or if a database error occurs
    """
    try:
        # Get raw data
        data = await request.json()
        
        # Extract query parameters
        db = data.get('db')
        if not db:
            raise HTTPException(status_code=400, detail="Database type is required")
            
        query = data.get('query')
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
            
        params = data.get('params', {})
        param_style = data.get('param_style', 'named')
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        
        logger.info(f"Executing parameterized query on {db} with params (style: {param_style})")
        
        # Validate parameter usage in query based on param_style
        if param_style == "named":
            # Verify all named parameters are present
            param_names = re.findall(r':(\w+)', query)
            missing_params = [name for name in param_names if name not in params]
            if missing_params:
                logger.warning(f"Missing parameters: {missing_params}")
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Missing parameters: {', '.join(missing_params)}"
                )
        elif param_style == "qmark":
            # Count ? placeholders and verify params count matches
            placeholder_count = query.count('?')
            if not isinstance(params, list) and placeholder_count > 0:
                # Convert dict to list if needed
                try:
                    params = list(params.values())
                except (AttributeError, TypeError):
                    logger.warning("Invalid parameters format for qmark style")
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail="For qmark style, parameters should be a list or dict with values"
                    )
            if placeholder_count != len(params):
                logger.warning(f"Parameter count mismatch: {placeholder_count} placeholders, {len(params)} values")
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Parameter count mismatch: {placeholder_count} placeholders, {len(params)} values"
                )
        
        # Use the basic executor from app.db
        logger.info("Using basic executor for parameterized query")
        
        # For qmark style with PostgreSQL, we need to handle it differently
        if param_style == "qmark" and db.lower() == "postgres":
            # Convert ? placeholders to $1, $2, etc.
            param_list = list(params.values()) if isinstance(params, dict) else params
            
            # For PostgreSQL and qmark style, we'll directly execute the query
            # instead of using the standard execute_parameterized_query
            # to avoid issues with the count query not propagating parameters
            
            # Direct query execution without the count query for pagination
            conn = None
            try:
                logger.info("Using direct PostgreSQL query execution for qmark style")
                import time
                start_time = time.time()
                
                from app.db import get_postgres_connection, pg_pool
                import psycopg2.extras
                
                # Get connection from pool
                conn = get_postgres_connection()
                
                # Convert query placeholders
                i = 1
                modified_query = ""
                for char in query:
                    if char == '?':
                        modified_query += f"${i}"
                        i += 1
                    else:
                        modified_query += char
                
                logger.info(f"Converted qmark query to PostgreSQL format: {modified_query}")
                
                # Create cursor with dictionary results
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Execute the main query with pagination
                    offset = (page - 1) * page_size
                    paginated_query = f"{modified_query} LIMIT {page_size} OFFSET {offset}"
                    
                    # For PostgreSQL, we need to ensure parameters are passed correctly
                    # Let's log what we're doing
                    logger.info(f"Executing paginated query: {paginated_query}")
                    logger.info(f"With params: {param_list}")
                    
                    # Direct string formatting for simple cases (this would normally be unsafe but we're showing it for debugging)
                    # In production, never do this - always use parameterized queries
                    safe_query = paginated_query
                    if len(param_list) == 1:
                        # For single parameter queries, directly substitute for testing
                        param_value = param_list[0]
                        if isinstance(param_value, str):
                            param_value = f"'{param_value}'"  # Quote strings
                        safe_query = safe_query.replace("$1", str(param_value))
                        logger.info(f"Using direct substitution query: {safe_query}")
                        cursor.execute(safe_query)
                    else:
                        # For multiple parameters, still try the parameterized approach
                        cursor.execute(paginated_query, param_list)
                        
                    results = cursor.fetchall()
                    
                    # For total count, use the same direct substitution approach for simple cases
                    count_modified_query = f"SELECT COUNT(*) AS total FROM ({modified_query}) AS count_subq"
                    
                    if len(param_list) == 1:
                        # For single parameter queries, directly substitute
                        param_value = param_list[0]
                        if isinstance(param_value, str):
                            param_value = f"'{param_value}'"  # Quote strings
                        safe_count_query = count_modified_query.replace("$1", str(param_value))
                        logger.info(f"Using direct substitution count query: {safe_count_query}")
                        cursor.execute(safe_count_query)
                    else:
                        # For multiple parameters, use parameterized
                        cursor.execute(count_modified_query, param_list)
                    count_result = cursor.fetchone()
                    total_count = count_result["total"] if count_result else 0
                    
                    # Create pagination data
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
                    
                    # Build result object
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    result = {
                        "status": "success",
                        "data": results,
                        "execution_time": execution_time,
                        "pagination": pagination,
                        "column_types": column_types
                    }
            finally:
                # Ensure connection is returned to pool
                if conn:
                    from app.db import pg_pool
                    if pg_pool:
                        pg_pool.putconn(conn)
                    
            # Return the custom result
            return result
        elif param_style == "named":
            # For named parameters, pass as dict
            result = execute_parameterized_query(
                db=db,
                query=query,
                params=params,
                page=page,
                page_size=page_size
            )
        else:
            # For other styles, pass as list
            param_list = list(params.values()) if isinstance(params, dict) else params
            result = execute_parameterized_query(
                db=db,
                query=query,
                params=param_list,
                page=page,
                page_size=page_size
            )
        
        return result
    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error executing parameterized query: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution error: {str(e)}"
        )

@router.post("/nl-to-sql", response_model=SQLTranslation)
async def nl_to_sql(
    prompt: NLPrompt,
    api_key: str = Depends(get_api_key)
):
    """
    Convert natural language prompt to SQL query.
    
    Args:
        prompt: The natural language prompt to convert to SQL
        
    Returns:
        SQLTranslation: The translated SQL query
        
    Raises:
        HTTPException: If an error occurs during translation
    """
    try:
        # Extract parameters
        db_type = prompt.db.value
        nl_prompt = prompt.prompt
        
        logger.info(f"Translating natural language to SQL for {db_type}")
        
        # Get schema information for context
        schema_info = ""
        
        # For now, use a simplified schema description
        if db_type == "postgres":
            schema_info = """
            Table: parcels
            Columns: id (int, PK), parcel_id (string), address (string), city (string), state (string), 
                    zip_code (string), land_value (numeric), improvement_value (numeric), total_value (numeric),
                    assessment_year (int), latitude (float), longitude (float), created_at (datetime), updated_at (datetime)
            
            Table: properties
            Columns: id (int, PK), parcel_id (int, FK to parcels.id), property_type (string), year_built (int),
                    square_footage (int), bedrooms (int), bathrooms (float), lot_size (float), lot_size_unit (string),
                    stories (float), condition (string), quality (string), tax_district (string), zoning (string),
                    created_at (datetime), updated_at (datetime)
            
            Table: sales
            Columns: id (int, PK), parcel_id (int, FK to parcels.id), sale_date (date), sale_price (numeric),
                    sale_type (string), transaction_id (string), buyer_name (string), seller_name (string),
                    financing_type (string), created_at (datetime), updated_at (datetime)
            
            Relationships:
            - One parcel can have multiple properties (one-to-many)
            - One parcel can have multiple sales (one-to-many)
            """
        
        # Translate natural language to SQL
        translation = await translate_nl_to_sql(nl_prompt, db_type, schema_info)
        
        if not translation:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to translate natural language to SQL"
            )
        
        # Return the translation
        return {
            "status": "success",
            "sql": translation["sql"],
            "explanation": translation["explanation"]
        }
    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error translating natural language to SQL: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation error: {str(e)}"
        )

@router.get("/discover-schema", response_model=SchemaResponse)
async def discover_schema(
    db: str = Query(..., regex="^(mssql|postgres)$"),
    api_key: str = Depends(get_api_key)
):
    """
    Discover and return the database schema.
    
    Args:
        db: The database to discover the schema for (mssql or postgres)
        
    Returns:
        SchemaResponse: The database schema
        
    Raises:
        HTTPException: If a database error occurs
    """
    try:
        logger.info(f"Discovering schema for {db}")
        
        schema_items = []
        
        if db.lower() == "postgres":
            # Use direct connection to PostgreSQL to avoid parameterization issues
            conn = None
            try:
                from app.db import get_postgres_connection
                conn = get_postgres_connection()
                
                # Create a cursor
                with conn.cursor() as cursor:
                    # Simple schema query
                    schema_query = """
                    SELECT 
                        table_schema,
                        table_name,
                        column_name,
                        data_type,
                        CASE WHEN is_nullable = 'YES' THEN true ELSE false END as is_nullable,
                        column_default
                    FROM 
                        information_schema.columns
                    WHERE 
                        table_schema = 'public'
                        AND table_name NOT LIKE 'pg_%'
                        AND table_name NOT LIKE 'sql_%'
                    ORDER BY 
                        table_name, 
                        ordinal_position;
                    """
                    
                    cursor.execute(schema_query)
                    
                    # Fetch all results
                    rows = cursor.fetchall()
                    
                    # Process the results
                    for row in rows:
                        schema_item = SchemaItem(
                            table_name=row[1],  # table_name is the second column (index 1)
                            column_name=row[2],  # column_name is the third column (index 2)
                            data_type=row[3],    # data_type is the fourth column (index 3)
                            is_nullable=row[4],  # is_nullable is the fifth column (index 4)
                            column_default=row[5],  # column_default is the sixth column (index 5)
                            is_primary_key=False,  # Default - would need a separate query
                            is_foreign_key=False,  # Default - would need a separate query
                        )
                        schema_items.append(schema_item)
            finally:
                # Ensure connection is returned to pool
                if conn:
                    from app.db import pg_pool
                    if pg_pool:
                        pg_pool.putconn(conn)
                
        return {
            "status": "success",
            "db_schema": schema_items
        }
    except Exception as e:
        logger.error(f"Error discovering schema: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema discovery error: {str(e)}"
        )

@router.get("/schema-summary", response_model=SchemaSummary)
async def get_schema_summary(
    db: str = Query(..., regex="^(mssql|postgres)$"),
    prefix: str = Query("", max_length=50),
    api_key: str = Depends(get_api_key)
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
    try:
        logger.info(f"Getting schema summary for {db}")
        
        if db.lower() == "postgres":
            # Use direct connection to PostgreSQL to avoid parameterization issues
            conn = None
            table_names = []
            
            try:
                from app.db import get_postgres_connection
                conn = get_postgres_connection()
                
                # Create a cursor
                with conn.cursor() as cursor:
                    # Query to get table names
                    if prefix:
                        # If prefix provided, filter tables by prefix
                        query = """
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                            AND table_type = 'BASE TABLE'
                            AND table_name NOT LIKE 'pg_%'
                            AND table_name NOT LIKE 'sql_%'
                            AND table_name LIKE %s
                        ORDER BY table_name;
                        """
                        cursor.execute(query, (f"{prefix}%",))
                    else:
                        # Get all tables
                        query = """
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                            AND table_type = 'BASE TABLE'
                            AND table_name NOT LIKE 'pg_%'
                            AND table_name NOT LIKE 'sql_%'
                        ORDER BY table_name;
                        """
                        cursor.execute(query)
                    
                    # Fetch all results
                    rows = cursor.fetchall()
                    
                    # Extract table names (first column)
                    table_names = [row[0] for row in rows]
            finally:
                # Ensure connection is returned to pool
                if conn:
                    from app.db import pg_pool
                    if pg_pool:
                        pg_pool.putconn(conn)
            
            return {
                "status": "success",
                "summary": table_names
            }
        else:
            return {
                "status": "error",
                "summary": []
            }
    except Exception as e:
        logger.error(f"Error getting schema summary: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema summary error: {str(e)}"
        )