"""
This module defines the API routes and handlers.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query
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
    # Test database connections
    db_connections = test_db_connections()
    
    return {
        "status": "success" if any(db_connections.values()) else "error",
        "message": "API is operational",
        "database_status": db_connections
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
    payload: ParameterizedSQLQuery,
    api_key: str = Depends(get_api_key)
):
    """
    Execute a parameterized SQL query against the specified database.
    
    This endpoint provides a secure way to execute SQL queries with proper parameter binding,
    which helps protect against SQL injection attacks. Parameters are passed separately
    from the query string and bound by the database driver.
    
    Args:
        payload: Contains the database type, SQL query with placeholders, parameter values,
                and optional pagination parameters
                
    Returns:
        QueryResult: The results of the SQL query with pagination metadata
        
    Raises:
        HTTPException: If the query is unsafe or if a database error occurs
    """
    try:
        # Extract query parameters
        db = payload.db.value
        query = payload.query
        params = payload.params or {}
        param_style = payload.param_style.value
        page = payload.page
        page_size = payload.page_size
        
        logger.info(f"Executing parameterized query on {db} with {len(params)} params")
        
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
        
        # Execute the query
        try:
            from app.query_executor import execute_parameterized_query as exec_query
            result = await exec_query(payload, allow_write=False)
            return result
        except ImportError:
            # Fallback to the db module function if query_executor isn't available
            if param_style == "named":
                # For named parameters, pass as dict
                result = execute_parameterized_query(
                    db=db,
                    query=query,
                    params=params,
                    page=page,
                    page_size=page_size
                )
            else:
                # For qmark, numeric, or format style, pass as list
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
            # For PostgreSQL, use the information_schema views
            # Query the database for schema information
            query = """
            SELECT 
                table_schema,
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default,
                pg_catalog.format_type(c.atttypid, c.atttypmod) as formatted_type
            FROM 
                information_schema.columns
                JOIN pg_catalog.pg_attribute c ON columns.column_name = c.attname
                JOIN pg_catalog.pg_class t ON c.attrelid = t.oid
                JOIN pg_catalog.pg_namespace n ON t.relnamespace = n.oid
            WHERE 
                table_schema = 'public'
                AND table_name NOT LIKE 'pg_%'
                AND table_name NOT LIKE 'sql_%'
            ORDER BY 
                table_name, 
                ordinal_position;
            """
            
            # This query might cause errors if pg_attribute relations are different
            # Using a simpler query as fallback
            try:
                result = execute_parameterized_query(db="postgres", query=query)
            except Exception:
                # Fallback to a simpler query
                query = """
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
                result = execute_parameterized_query(db="postgres", query=query)
            
            # Process the results
            for row in result["data"]:
                schema_item = SchemaItem(
                    table_name=row["table_name"],
                    column_name=row["column_name"],
                    data_type=row.get("formatted_type", row["data_type"]),
                    is_nullable=row["is_nullable"],
                    column_default=row["column_default"],
                    is_primary_key=False,  # Would need additional query for this
                    is_foreign_key=False,  # Would need additional query for this
                )
                schema_items.append(schema_item)
                
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
            # Query to get table names
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE 'pg_%'
                AND table_name NOT LIKE 'sql_%'
            ORDER BY table_name;
            """
            
            if prefix:
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
                result = execute_parameterized_query(db="postgres", query=query, params=[f"{prefix}%"])
            else:
                result = execute_parameterized_query(db="postgres", query=query)
            
            # Extract table names
            table_names = [row["table_name"] for row in result["data"]]
            
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