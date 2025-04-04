"""
This module defines the API routes and handlers.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from starlette.responses import JSONResponse

from app.db import execute_parameterized_query, parse_for_parameters, test_db_connections
from app.models import (
    HealthResponse, 
    NLPrompt, 
    SQLQuery, 
    SQLTranslation,
    SchemaResponse,
    SchemaSummary
)
from app.security import get_api_key
from app.settings import Settings

settings = Settings()

# Create API router
router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check the health of the API and its database connections.
    
    Returns:
        HealthResponse: The health status of the API and its database connections
    """
    # Test database connections
    db_status = test_db_connections()
    
    return {
        "status": "success",
        "message": "API is operational",
        "timestamp": datetime.utcnow().isoformat(),
        "database_status": db_status
    }


@router.post("/run-query", tags=["Query"])
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
        # Parse the query to extract parameters
        parsed_query, params = parse_for_parameters(payload.query)
        
        # Execute the parameterized query
        result = execute_parameterized_query(
            db=payload.db,
            query=parsed_query,
            params=params,
            page=payload.page,
            page_size=payload.page_size
        )
        
        return result
    except Exception as e:
        # Log the error
        print(f"Error executing query: {e}")
        
        # If this is already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        
        # Otherwise, wrap it in an appropriate HTTP error
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {str(e)}"
        )


@router.post("/nl-to-sql", response_model=SQLTranslation, tags=["Natural Language"])
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
        # Check if OpenAI API key is available
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."
            )
        
        # Import here to avoid circular imports
        from app.openai_service import translate_nl_to_sql
        
        # Get database schema to provide context for translation
        schema_info = "Sample schema information for real estate property data:"
        
        if prompt.db.lower() == 'postgres':
            schema_info += """
            Tables:
            - parcels: Contains property assessment records with columns like parcel_id, address, city, state, zip_code, land_value, improvement_value, total_value, assessment_year, latitude, longitude
            - properties: Contains physical property characteristics with columns like property_type, year_built, square_footage, bedrooms, bathrooms, lot_size, lot_size_unit, stories, condition, quality, tax_district, zoning
            - sales: Contains property sale history with columns like sale_date, sale_price, sale_type, transaction_id, buyer_name, seller_name, financing_type
            
            Relationships:
            - properties.parcel_id references parcels.id
            - sales.parcel_id references parcels.id
            """
        
        # Call OpenAI to translate the prompt
        translation_result = await translate_nl_to_sql(prompt.prompt, prompt.db, schema_info)
        
        return {
            "query": translation_result["query"],
            "explanation": translation_result["explanation"],
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        # If this is already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        
        # Otherwise, wrap it in an appropriate HTTP error
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error translating natural language to SQL: {str(e)}"
        )


@router.get("/discover-schema", response_model=SchemaResponse, tags=["Schema"])
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
        if db.lower() == 'postgres':
            # PostgreSQL schema query - get tables, columns, constraints
            schema_query = """
            SELECT 
                t.table_name,
                t.table_schema,
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.constraint_name IS NOT NULL THEN TRUE ELSE FALSE END as is_primary,
                pgd.description as column_description
            FROM 
                information_schema.tables t
            JOIN 
                information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            LEFT JOIN 
                (
                    SELECT tc.constraint_name, tc.table_name, kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                ) pk ON t.table_name = pk.table_name AND c.column_name = pk.column_name
            LEFT JOIN 
                pg_catalog.pg_statio_all_tables st ON t.table_schema = st.schemaname AND t.table_name = st.relname
            LEFT JOIN 
                pg_catalog.pg_description pgd ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
            WHERE 
                t.table_schema = 'public'
            ORDER BY 
                t.table_name, c.ordinal_position;
            """
            
            # Get relationship information
            fk_query = """
            SELECT
                tc.table_schema, 
                tc.constraint_name, 
                tc.table_name, 
                kcu.column_name, 
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM 
                information_schema.table_constraints AS tc 
            JOIN 
                information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN 
                information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE 
                tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public';
            """
            
            # Get row counts
            row_count_query = """
            SELECT 
                relname as table_name, 
                n_live_tup as row_count
            FROM 
                pg_stat_user_tables
            WHERE 
                schemaname = 'public';
            """
            
            # Execute queries
            schema_data = execute_parameterized_query(db, schema_query)
            fk_data = execute_parameterized_query(db, fk_query)
            row_count_data = execute_parameterized_query(db, row_count_query)
            
            # Process the results
            tables = {}
            
            # First process column info
            for row in schema_data['data']:
                table_name = row['table_name']
                schema_name = row['table_schema']
                
                if table_name not in tables:
                    tables[table_name] = {
                        'name': table_name,
                        'schema': schema_name,
                        'columns': [],
                        'relationships': [],
                        'row_count': None,
                        'description': None
                    }
                
                # Add column info
                tables[table_name]['columns'].append({
                    'name': row['column_name'],
                    'type': row['data_type'],
                    'is_primary': row['is_primary'],
                    'is_nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default'],
                    'description': row['column_description']
                })
            
            # Add row counts
            for row in row_count_data['data']:
                table_name = row['table_name']
                if table_name in tables:
                    tables[table_name]['row_count'] = row['row_count']
            
            # Process relationships
            for row in fk_data['data']:
                table_name = row['table_name']
                if table_name in tables:
                    tables[table_name]['relationships'].append({
                        'table': row['foreign_table_name'],
                        'from_column': row['column_name'],
                        'to_column': row['foreign_column_name'],
                        'type': 'many-to-one'  # Default relationship type
                    })
            
            # Construct the final response
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'database': db,
                'tables': list(tables.values())
            }
        
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Unsupported database type: {db}"
            )
    
    except Exception as e:
        # If this is already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        
        # Otherwise, wrap it in an appropriate HTTP error
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error discovering database schema: {str(e)}"
        )


@router.get("/schema-summary", response_model=SchemaSummary, tags=["Schema"])
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
        if db.lower() == 'postgres':
            # Build the query with optional filtering
            where_clause = "WHERE t.table_schema = 'public'"
            params = []
            
            if prefix:
                where_clause += " AND t.table_name LIKE %s"
                params.append(f"{prefix}%")
            
            # PostgreSQL schema summary query
            summary_query = f"""
            SELECT 
                t.table_name,
                COUNT(c.column_name) as column_count,
                obj_description(QUOTE_IDENT(t.table_name)::regclass::oid) as description,
                (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname = t.table_name) as row_count
            FROM 
                information_schema.tables t
            JOIN 
                information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            {where_clause}
            GROUP BY 
                t.table_name
            ORDER BY 
                t.table_name;
            """
            
            # Execute query
            result = execute_parameterized_query(db, summary_query, params)
            
            # Construct the table summaries
            tables = []
            for row in result['data']:
                tables.append({
                    'name': row['table_name'],
                    'column_count': row['column_count'],
                    'row_count': row['row_count'],
                    'description': row['description']
                })
            
            # Construct the final response
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'database': db,
                'table_count': len(tables),
                'tables': tables,
                'filtered': bool(prefix)
            }
        
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Unsupported database type: {db}"
            )
    
    except Exception as e:
        # If this is already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        
        # Otherwise, wrap it in an appropriate HTTP error
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting schema summary: {str(e)}"
        )